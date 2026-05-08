"""
Fix Agent 节点函数
每个函数对应 StateGraph 中的一个节点，接收 state dict，返回更新的 state dict
"""

import json
import logging
import os
import re
import subprocess
import sys

# 将 ai_apply 目录加入 path，以便导入 ai_client 和 code_renderer
_AI_APPLY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_APPLY_DIR not in sys.path:
    sys.path.insert(0, _AI_APPLY_DIR)

from ai_client import AIClient
from code_renderer import render_and_save

from .schemas import ERROR_ANALYSIS_TOOL
from .analysis_prompts import ANALYSIS_SYSTEM_PROMPT


logger = logging.getLogger("fix_agent")

# ==================== 内部函数 ====================

def _run_pytest(test_file: str) -> str:
    """执行 pytest 并返回输出"""
    try:
        # 等价于你在终端里手动敲：pytest test_loadmodel_chain.py -v --tb=short
        result = subprocess.run(
            ["pytest", test_file, "-v", "--tb=short"],
            capture_output=True, text=True, timeout=120,
        )
        # 执行完后 result.stdout + "\n" + result.stderr 拿到完整的 pytest 输出文本，后面用正则解析哪些用例失败了。
        return result.stdout + "\n" + result.stderr
    except subprocess.TimeoutExpired:
        return "FAILED - pytest 执行超时（120s）"
    except Exception as e:
        return f"FAILED - pytest 执行异常: {e}"


# ==================== 辅助函数 ====================

def _load_json(out_dir: str, filename: str) -> dict | None:
    filepath = os.path.join(out_dir, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_json(data: dict, out_dir: str, filename: str) -> str:
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


# ==================== 节点函数 ====================

def load_artifacts(state: dict) -> dict:
    """加载 scenarios.json / semantics.json / workflow.json"""

    # graph = StateGraph(FixState)
    # graph.add_node("load_artifacts", load_artifacts)
    # state由以上操作更新

    out_dir = state["test_output_dir"]
    logger.info("加载产物: %s", out_dir)

    scenarios = _load_json(out_dir, "scenarios.json")
    if not scenarios:
        raise FileNotFoundError(f"未找到 {out_dir}/scenarios.json，请先运行 pipeline")

    semantics = _load_json(out_dir, "semantics.json")
    workflow = _load_json(out_dir, "workflow.json")

    updates = {
        "scenarios": scenarios,
        "semantics": semantics or {},
        "workflow": workflow or {},
    }
    if "retry_count" not in state:
        updates["retry_count"] = 0
    if "history" not in state:
        updates["history"] = []

    return updates


def parse_pytest_output(state: dict) -> dict:
    """解析 pytest 输出，提取失败用例信息"""

    raw = state.get("pytest_output", "")
    if not raw:
        logger.info("无 pytest 输出，需要执行测试")
        # 尝试执行 pytest
        out_dir = state["test_output_dir"]
        test_files = [f for f in os.listdir(out_dir) if f.startswith("test_") and f.endswith(".py")]
        if test_files:
            # 如果 state 里有没有 pytest_output，自己跑一次 pytest 获取输出
            raw = _run_pytest(os.path.join(out_dir, test_files[0]))
        else:
            return {"failed_tests": [], "all_passed": True}

    failed_tests = []
    # 匹配 FAILED 行
    failed_pattern = re.compile(r"FAILED\s+(.+?)::(\w+)::(\w+)\s*-")
    # 匹配 AssertionError 或 Error 信息
    error_blocks = re.split(r"={3,}\s*FAILURES\s*={3,}", raw)

    for match in failed_pattern.finditer(raw):
        test_file, class_name, test_name = match.group(1), match.group(2), match.group(3)
        error_msg = ""
        traceback_snippet = ""

        # 从 error_blocks 中查找对应的 traceback
        for block in error_blocks[1:]:
            if test_name in block:
                # strip() - 去掉字符串首尾的空白字符（空格、换行、制表符）
                # split("\n") - 按换行符分割成列表
                lines = block.strip().split("\n")
                # 提取最后几行作为错误摘要
                error_lines = [l.strip() for l in lines if l.strip() and not l.strip().startswith("_")]
                if error_lines:
                    error_msg = error_lines[-1][:200]
                traceback_snippet = "\n".join(lines[-10:])[:500]
                break

        failed_tests.append({
            "test_name": test_name,
            "class_name": class_name,
            "test_file": test_file,
            "error_message": error_msg,
            "traceback": traceback_snippet,
        })

    # 如果有 FAILED 但正则没匹配到，做兜底
    if "FAILED" in raw and not failed_tests:
        failed_tests.append({
            "test_name": "unknown",
            "class_name": "",
            "test_file": "",
            "error_message": "pytest 输出中包含 FAILED 但无法解析具体用例",
            "traceback": raw[-500:],
        })

    logger.info("解析到 %d 个失败用例", len(failed_tests))
    if not failed_tests and "passed" in raw:
        logger.info("所有测试通过")

    return {
        "failed_tests": failed_tests,
        "all_passed": len(failed_tests) == 0,
    }


def human_review(state: dict) -> dict:
    """
    人工审核节点。
    此节点通过 LangGraph interrupt 机制暂停，runner 层负责交互。
    实际的 approve/reject/modify 由 runner 在恢复时写入 state。
    """
    
    # 如果已经有 human_decision，说明是恢复后的运行，直接透传
    decision = state.get("human_decision")
    if decision:
        logger.info("人工审核结果: %s", decision)
        if decision == "modify" and state.get("human_modification"):
            return {"fix_details": state["human_modification"].get("fix_details", state.get("fix_details", []))}
    return {}


def apply_fix(state: dict) -> dict:
    """按修复方案修改 scenarios.json"""

    fix_details = state.get("fix_details", [])
    if not fix_details:
        logger.warning("无修复方案可执行")
        return {}

    scenarios = state["scenarios"]
    applied = 0

    for detail in fix_details:
        target_func = detail.get("interface_func", "")
        target_scenario = detail.get("scenario_name", "")
        field = detail.get("field_to_change", "")
        proposed = detail.get("proposed_value", "")

        # 定位目标接口
        for iface in scenarios.get("interfaces", []):
            if iface["func"] != target_func:
                continue

            # 定位目标场景
            for i, scenario in enumerate(iface.get("test_scenarios", [])):
                if scenario["name"] != target_scenario:
                    continue

                if field == "__remove__":
                    iface["test_scenarios"].pop(i)
                    applied += 1
                    logger.info("删除场景: %s/%s", target_func, target_scenario)
                    break

                try:
                    new_value = json.loads(proposed)
                except (json.JSONDecodeError, TypeError):
                    new_value = proposed

                if field == "args":
                    scenario["args"] = new_value
                    applied += 1
                elif field == "expected.should_success":
                    scenario.setdefault("expected", {})["should_success"] = new_value
                    applied += 1
                elif field == "expected.assertions":
                    scenario.setdefault("expected", {})["assertions"] = new_value
                    applied += 1
                elif field == "category":
                    scenario["category"] = new_value
                    applied += 1
                elif field == "description":
                    scenario["description"] = new_value
                    applied += 1

                logger.info("修改 %s/%s.%s: %s → %s",
                            target_func, target_scenario, field,
                            detail.get("current_value", "?"), proposed)
                break

    # 保存修改后的 scenarios.json
    out_dir = state["test_output_dir"]
    path = _save_json(scenarios, out_dir, "scenarios.json")
    logger.info("已应用 %d 处修改，保存至 %s", applied, path)

    return {"scenarios": scenarios}


def re_render(state: dict) -> dict:
    """重新渲染测试代码"""

    scenario_name = state["scenario_name"]
    scenarios = state["scenarios"]

    logger.info("重新渲染测试代码: %s", scenario_name)
    file_path = render_and_save(scenario_name, scenarios)
    logger.info("渲染完成: %s", file_path)

    return {"re_rendered": True}


def retest(state: dict) -> dict:
    """执行 pytest 验证修复"""

    out_dir = state["test_output_dir"]
    retry_count = state.get("retry_count", 0) + 1
    max_retries = state.get("max_retries", 3)

    logger.info("执行第 %d/%d 次测试验证", retry_count, max_retries)

    # 找到测试文件
    test_files = [f for f in os.listdir(out_dir) if f.startswith("test_") and f.endswith(".py")]
    if not test_files:
        return {
            "retry_count": retry_count,
            "retest_output": "未找到测试文件",
            "all_passed": False,
            "history": state.get("history", []) + [{
                "retry": retry_count,
                "category": state.get("error_category", ""),
                "action": state.get("fix_action", ""),
                "result": "error: no test file",
            }],
        }

    test_path = os.path.join(out_dir, test_files[0])
    output = _run_pytest(test_path)
    passed = "FAILED" not in output

    logger.info("测试结果: %s", "全部通过" if passed else "仍有失败")

    history_entry = {
        "retry": retry_count,
        "category": state.get("error_category", ""),
        "action": state.get("fix_action", ""),
        "result": "passed" if passed else "failed",
    }

    return {
        "retry_count": retry_count,
        "retest_output": output,
        "all_passed": passed,
        "pytest_output": output,  # 供下一轮 analyze_failure 使用
        "failed_tests": [],       # 会在 parse_pytest_output 中重新解析
        "history": state.get("history", []) + [history_entry],
    }


def analyze_failure(state: dict) -> dict:
    """AI 分析失败原因并分类"""

    failed_tests = state.get("failed_tests", [])
    if not failed_tests:
        return {"error_category": "uncertain", "root_cause": "无失败用例", "affected_interfaces": []}

    logger.info("AI 分析失败原因（第 %d 次重试）", state.get("retry_count", 0))

    # 构建上下文：失败信息 + 相关语义 + 当前场景
    user_parts = ["## 测试失败信息\n"]
    for ft in failed_tests:
        user_parts.append(f"- 测试: {ft['test_name']}")
        user_parts.append(f"  错误: {ft['error_message']}")
        if ft.get("traceback"):
            user_parts.append(f"  Traceback:\n```\n{ft['traceback']}\n```")
        user_parts.append("")

    # 添加受影响接口的语义信息
    affected = set()
    for ft in failed_tests:
        # 从测试名提取接口函数名，如 test_loadModel_normal -> loadModel
        name = ft["test_name"]
        for iface in state.get("semantics", {}).get("interfaces", []):
            if iface["func"].split(".")[-1] in name:
                affected.add(iface["func"])

    if affected:
        user_parts.append("## 相关接口语义信息\n")
        for iface in state.get("semantics", {}).get("interfaces", []):
            if iface["func"] in affected:
                user_parts.append(f"### {iface['func']}")
                user_parts.append(f"业务含义: {iface.get('business_meaning', '')}")
                if iface.get("params"):
                    user_parts.append("参数约束:")
                    for p in iface["params"]:
                        user_parts.append(f"  - {p.get('params_name', p.get('index', '?'))}: "
                                         f"类型={p.get('type', '?')}, "
                                         f"范围={p.get('valid_range', '?')}, "
                                         f"枚举={p.get('enum_values', [])}")
                user_parts.append("")

    # 添加当前场景数据（仅受影响接口）
    if affected:
        user_parts.append("## 当前测试场景\n")
        for iface in state.get("scenarios", {}).get("interfaces", []):
            if iface["func"] in affected:
                user_parts.append(f"### {iface['func']}")
                for s in iface.get("test_scenarios", []):
                    user_parts.append(f"- {s['name']} ({s['category']}): args={s.get('args', [])}, "
                                     f"expected={s.get('expected', {})}")
                user_parts.append("")

    # 添加历史修复记录（避免重复策略）
    history = state.get("history", [])
    if history:
        user_parts.append("## 之前的修复尝试（请勿重复相同策略）\n")
        for h in history:
            user_parts.append(f"- 第 {h['retry']} 次: category={h['category']}, "
                             f"action={h['action']}, 结果={h['result']}")

    user_message = "\n".join(user_parts)

    # 调用 AI
    client = AIClient()
    try:
        result = client.call(
            system_prompt=ANALYSIS_SYSTEM_PROMPT,
            user_message=user_message,
            tool=ERROR_ANALYSIS_TOOL,
        )
    except Exception as e:
        logger.error("AI 分析失败: %s", e)
        return {
            "error_category": "uncertain",
            "root_cause": f"AI 调用失败: {e}",
            "affected_interfaces": list(affected),
            "fix_proposal_confidence": 0.0,
        }

    return {
        "error_category": result.get("error_category", "uncertain"),
        "root_cause": result.get("root_cause", ""),
        "affected_interfaces": result.get("affected_interfaces", list(affected)),
        "fix_proposal_confidence": result.get("confidence", 0.5),
    }


def skill_dispatch(state: dict) -> dict:
    """
    Skill 调度节点：根据 error_category 查找并执行对应 skill。
    替代原先的 propose_fix（通用 AI 修复）和 handle_environment（环境终止）。
    """

    from .skills.registry import SkillRegistry

    # # 1. 拿到 AI 分析出的错误分类
    category = state.get("error_category", "uncertain")
    
    # # 2. 从注册表里找对应的 skill
    registry = SkillRegistry()
    skill = registry.get_skill(category)

    # # 3. 如果没找到，使用 uncertain 回退
    if skill is None:
        logger.warning("未找到 category=%s 的 skill，使用 uncertain 回退", category)
        skill = registry.get_skill("uncertain")

    logger.info("调度 skill: %s (category=%s, deterministic=%s)",
                skill.name, skill.category, skill.is_deterministic)

    # # 4. 交给 skill 执行，拿到修复方案
    result = skill.execute(state)

    # 记录到历史
    history = state.get("history", [])
    history.append({
        "retry": state.get("retry_count", 0),
        "category": category,
        "action": result.get("fix_action", ""),
        "result": f"skill:{skill.name}",
    })
    result["history"] = history

    return result
