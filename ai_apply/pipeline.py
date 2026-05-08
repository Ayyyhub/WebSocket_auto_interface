"""
AI 生成式接口自动化测试 - 主流程入口（7 步解耦架构）

流程：
  ① 轻量 AST 提取（确定性）           → raw_interfaces.json
  ② 钉钉文档获取（可选）              → dingtalk_docs.json
  ③ 确定性工作流分析 + 钉钉文档合并    → workflow.json
  ④ AI 语义分析   （第 1 次 AI）      → semantics.json
  ⑤ AI 测试场景生成（第 2 次 AI）     → scenarios.json
  ⑥ 模板渲染（确定性）                → test_xxx.py
  ⑦ 执行测试（可选）

每一步产出独立产物，出问题可精确定位到具体步骤。

用法:
  python pipeline.py loadmodel               # 解析 loadmodel_chain
  python pipeline.py ../Service/init_chain.py  # 解析指定文件
  python pipeline.py --execute                # 生成后立即执行
  python pipeline.py --refresh-docs           # 强制刷新钉钉文档缓存
  python pipeline.py --step 3 loadmodel       # 只运行第 3 步（调试用）
"""

import argparse
import json
import os
import subprocess

from workflow_parser import parse_workflow, parse_workflow_enhanced, format_for_ai, format_workflow_for_generator, merge_with_dingtalk_docs
from semantic_parser import parse_semantics, format_semantics_for_generator
from scenario_generator import generate_test_scenarios
from ai_client import load_llm_config
from data_builder import TestDataBuilder
from code_renderer import render_and_save_workflow
from dingtalk_doc import DingTalkDocClient
import datetime

_HERE = os.path.dirname(os.path.abspath(__file__))
SERVICE_DIR = os.path.join(os.path.dirname(_HERE), "Service")
OUTPUT_DIR = os.path.join(os.path.dirname(_HERE), "ai_generated_testcases")


def _output_dir(scenario_name: str) -> str:
    """获取输出目录（同名自动加时间戳后缀）"""
    out_dir = os.path.join(OUTPUT_DIR, scenario_name)
    if os.path.exists(out_dir):
        i = datetime.datetime.now().timestamp()
        out_dir = os.path.join(OUTPUT_DIR, f"{scenario_name}_{i}")
    os.makedirs(out_dir, exist_ok=True)
    return out_dir


def _save_json(data, out_dir, filename):
    """保存 JSON 产物"""
    filepath = os.path.join(out_dir, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return filepath


def _load_json(out_dir, filename):
    """加载已保存的 JSON 产物（用于跳步调试）"""
    filepath = os.path.join(out_dir, filename)
    if not os.path.exists(filepath):
        return None
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def run(source: str = None, execute: bool = False, refresh_docs: bool = False,
        step: int = None):
    """
    主流程入口。

    :param source: 源文件路径或场景名（如 loadmodel）
    :param execute: 是否在生成后执行测试
    :param refresh_docs: 是否强制刷新钉钉文档缓存
    :param step: 只运行指定步骤（调试用，None 则运行全部）
    """
    # ========== 确定目标文件 ==========
    if source:
        if source.endswith(".py"):
            target_file = os.path.abspath(source)
        else:
            target_file = os.path.join(SERVICE_DIR, f"{source}_chain.py")
        scenario_name = os.path.splitext(os.path.basename(target_file))[0]
    else:
        target_file = None
        scenario_name = "all_interfaces"

    out_dir = _output_dir(scenario_name)
    llm_config = load_llm_config()

    # ========== ① 轻量 AST 提取（确定性） ==========
    if step is None or step == 1:
        print("=" * 60)
        print("① 轻量 AST 提取（确定性）")
        print("=" * 60)

        if not target_file:
            print("未指定源文件，退出")
            return

        raw_workflow = parse_workflow(target_file)
        interfaces = raw_workflow["interfaces"]

        print(f"工作流: {raw_workflow['workflow_name']}")
        print(f"提取到 {len(interfaces)} 个 send_request 调用\n")

        if not interfaces:
            print("未提取到任何接口，退出")
            return

        raw_path = _save_json(raw_workflow, out_dir, "raw_interfaces.json")
        print(f"产物: {raw_path}")

        api_text = format_for_ai(raw_workflow)
        print(api_text)

        if step == 1:
            return  # 只跑第 1 步
    else:
        # 跳步：加载已有产物
        raw_workflow = _load_json(out_dir, "raw_interfaces.json")
        if not raw_workflow:
            print(f"错误：未找到 {out_dir}/raw_interfaces.json，请先运行第 1 步")
            return
        interfaces = raw_workflow["interfaces"]
        api_text = format_for_ai(raw_workflow)
        print(f"跳步：加载已有 raw_interfaces.json（{len(interfaces)} 个接口）")

    # ========== ② 钉钉文档获取（可选） ==========
    dingtalk_docs = None
    if step is None or step == 2:
        if refresh_docs:
            print("\n" + "=" * 60)
            print("② 从钉钉文档获取接口完整定义")
            print("=" * 60)

            doc_skill = DingTalkDocClient()
            interface_names = [iface["func"] for iface in interfaces]
            print(f"需要获取 {len(interface_names)} 个接口的文档\n")

            dingtalk_docs = doc_skill.get_interface_docs(
                interface_names, force_refresh=refresh_docs
            )

            if dingtalk_docs:
                docs_path = _save_json(dingtalk_docs, out_dir, "dingtalk_docs.json")
                cache_count = sum(1 for d in dingtalk_docs.values() if d.get("source") == "cache")
                api_count = sum(1 for d in dingtalk_docs.values() if d.get("source") == "api")
                print(f"产物: {docs_path}")
                print(f"来源: {cache_count} 缓存, {api_count} API")
            else:
                print("未获取到钉钉文档，继续使用本地数据")
        else:
            print("\n② 跳过钉钉文档获取（使用 --refresh-docs 启用）")
            # 尝试加载已有缓存
            dingtalk_docs = _load_json(out_dir, "dingtalk_docs.json")

        if step == 2:
            return
    else:
        dingtalk_docs = _load_json(out_dir, "dingtalk_docs.json")

    # ========== ③ 确定性工作流分析 ==========
    workflow = None
    if step is None or step == 3:
        print("\n" + "=" * 60)
        print("③ 确定性工作流分析（变量追踪 + 钉钉文档合并）")
        print("=" * 60)

        workflow = parse_workflow_enhanced(target_file)
        workflow = merge_with_dingtalk_docs(workflow, dingtalk_docs)

        wf_path = _save_json(workflow, out_dir, "workflow.json")
        print(f"产物: {wf_path}")
        print(f"接口数: {len(workflow.get('interfaces', []))}")
        print(f"状态变量: {len(workflow.get('state_flow', []))}")
        print(f"子工作流: {len(workflow.get('sub_workflows', []))}")
        if step == 3:
            return
    else:
        workflow = _load_json(out_dir, "workflow.json")
        if workflow:
            print(f"跳步：加载已有 workflow.json")

    workflow_text = format_workflow_for_generator(workflow) if workflow else ""

    # ========== ④ AI 语义分析（第 1 次 AI） ==========
    semantics = None
    if step is None or step == 4:
        print("\n" + "=" * 60)
        print("④ AI 语义分析（第 1 次 AI 调用）")
        print("=" * 60)
        print(f"模型: {llm_config.get('model')}")

        BATCH_SIZE = 5
        all_semantics = {"interfaces": []}

        for batch_start in range(0, len(interfaces), BATCH_SIZE):
            batch = interfaces[batch_start:batch_start + BATCH_SIZE]
            batch_text = format_for_ai({"interfaces": batch, "workflow_name": raw_workflow["workflow_name"], "source_file": raw_workflow["source_file"]})
            print(f"\n分析第 {batch_start + 1}-{batch_start + len(batch)} 个接口...")

            for attempt in range(3):
                try:
                    batch_semantics = parse_semantics(
                        batch_text, workflow_text=workflow_text, config=llm_config
                    )
                    result_ifaces = batch_semantics.get("interfaces", [])

                    # 校验：AI 必须返回与输入数量一致的接口
                    if len(result_ifaces) < len(batch):
                        print(f"  警告: 输入 {len(batch)} 个接口，AI 只返回 {len(result_ifaces)} 个"
                              f"（第 {attempt + 1} 次尝试），重试...")
                        if attempt < 2:
                            continue
                        print(f"  重试耗尽，接受已有结果")

                    all_semantics["interfaces"].extend(result_ifaces)
                    print(f"  完成（{len(result_ifaces)}/{len(batch)} 个接口）")
                    break
                except json.JSONDecodeError:
                    print(f"  第 {attempt + 1} 次尝试失败，重试...")
                    if attempt == 2:
                        print(f"  跳过本批")
                except Exception as e:
                    print(f"  失败: {e}")
                    break

        semantics_path = _save_json(all_semantics, out_dir, "semantics.json")
        print(f"\n产物: {semantics_path}")
        semantics_text = format_semantics_for_generator(all_semantics)
        print(semantics_text)
        semantics = all_semantics
    else:
        semantics = _load_json(out_dir, "semantics.json")

    semantics_text = format_semantics_for_generator(semantics) if semantics else ""

    # ========== ⑤ AI 测试场景生成（第 2 次 AI） ==========
    scenarios = None
    if step is None or step == 5:
        print("\n" + "=" * 60)
        print("⑤ AI 测试场景生成（第 2 次 AI 调用）")
        print("=" * 60)

        BATCH_SIZE = 5
        all_scenarios = []

        for batch_start in range(0, len(interfaces), BATCH_SIZE):
            batch = interfaces[batch_start:batch_start + BATCH_SIZE]
            batch_text = format_for_ai({"interfaces": batch, "workflow_name": raw_workflow["workflow_name"], "source_file": raw_workflow["source_file"]})

            batch_semantics = {"interfaces": semantics["interfaces"][batch_start:batch_start + BATCH_SIZE]} if semantics else {"interfaces": []}
            batch_semantics_text = format_semantics_for_generator(batch_semantics)

            print(f"\n生成第 {batch_start + 1}-{batch_start + len(batch)} 个接口的测试场景...")

            for attempt in range(3):
                try:
                    batch_result = generate_test_scenarios(
                        interfaces_text=batch_text,
                        semantics_text=batch_semantics_text,
                        config=llm_config,
                    )
                    result_ifaces = batch_result.get("interfaces", [])

                    # 校验：AI 必须返回与输入数量一致的接口
                    if len(result_ifaces) < len(batch):
                        missing = len(batch) - len(result_ifaces)
                        print(f"  警告: 输入 {len(batch)} 个接口，AI 只返回 {len(result_ifaces)} 个"
                              f"（缺少 {missing} 个，第 {attempt + 1} 次尝试），重试...")
                        if attempt < 2:
                            continue
                        print(f"  重试耗尽，接受已有结果")

                    all_scenarios.extend(result_ifaces)
                    count = sum(len(i.get("test_scenarios", [])) for i in result_ifaces)
                    print(f"  本批生成 {count} 个测试场景（{len(result_ifaces)}/{len(batch)} 个接口）")
                    break
                except json.JSONDecodeError:
                    print(f"  第 {attempt + 1} 次尝试失败，重试...")
                    if attempt == 2:
                        print(f"  跳过本批")
                except Exception as e:
                    print(f"  失败: {e}")
                    break

        if not all_scenarios:
            print("未生成任何测试场景，退出")
            return

        # 全局校验：检查是否有接口缺失
        if len(all_scenarios) < len(interfaces):
            expected_funcs = [iface["func"] for iface in interfaces]
            returned_funcs = [iface["func"] for iface in all_scenarios]
            missing_funcs = [f for f in expected_funcs if f not in returned_funcs]
            # 注意：重复 func 名只报告一次
            print(f"\n⚠ 警告: 共 {len(interfaces)} 个接口，只生成了 {len(all_scenarios)} 个的场景")
            if missing_funcs:
                print(f"  缺失接口: {missing_funcs}")

        scenarios = {"interfaces": all_scenarios}
        total = sum(len(i.get("test_scenarios", [])) for i in all_scenarios)
        print(f"\n共 {len(all_scenarios)} 个接口，{total} 个测试场景")

        scenarios_path = _save_json(scenarios, out_dir, "scenarios.json")
        print(f"产物: {scenarios_path}")

    # ========== ⑤.5 测试数据填充（确定性） ==========
    if scenarios and semantics:
        print("\n" + "-" * 60)
        print("⑤.5 根据语义约束填充测试数据（确定性）")
        print("-" * 60)

        # 根据语义约束填充测试数据
        scenarios = TestDataBuilder(semantics).fill(scenarios)
        
        filled = sum(1 for i in scenarios.get("interfaces", [])
                     for s in i.get("test_scenarios", []) if s.get("args"))
        print(f"已填充 {filled} 个场景的测试数据")
        _save_json(scenarios, out_dir, "scenarios.json")

    # ========== ⑥ 模板渲染（确定性） ==========
    if step is None or step == 6:
        print("\n" + "=" * 60)
        print("⑥ 渲染工作流链式测试")
        print("=" * 60)

        if workflow and workflow.get("state_flow"):
            actual_name = os.path.basename(out_dir)
            wf_path = render_and_save_workflow(actual_name, workflow, scenarios)
            print(f"产物: {wf_path}")
        else:
            print("无工作流数据（state_flow 为空），跳过")

    # ========== 汇总 ==========
    print("\n" + "=" * 60)
    print("完成！产物清单：")
    print("=" * 60)
    print(f"  输出目录: {out_dir}/")
    for f in ["raw_interfaces.json", "dingtalk_docs.json", "workflow.json",
              "semantics.json", "scenarios.json"]:
        fp = os.path.join(out_dir, f)
        if os.path.exists(fp):
            print(f"  ✅ {f}")
        else:
            print(f"  ⏭️  {f}（未生成）")

    # ========== ⑦ 执行测试（可选） ==========
    if execute and (step is None or step == 7):
        print("\n" + "=" * 60)
        print("⑦ 执行生成的测试用例")
        print("=" * 60)
        # 找到测试文件
        test_files = [f for f in os.listdir(out_dir) if f.startswith("test_") and f.endswith(".py")]
        if test_files:
            subprocess.run(["pytest", os.path.join(out_dir, test_files[0]), "-v", "--tb=short"])
        else:
            print("未找到测试文件")


def main():
    parser = argparse.ArgumentParser(description="AI 生成式接口自动化测试（7 步解耦架构）")
    parser.add_argument("source", nargs="?", default=None,
                        help="指定源：文件路径、场景名（如 loadmodel），留空则解析全部")
    parser.add_argument("--execute", action="store_true", help="生成后立即执行测试")
    parser.add_argument("--refresh-docs", action="store_true",
                        help="强制刷新钉钉文档缓存")
    parser.add_argument("--step", type=int, default=None,
                        help="只运行指定步骤（1-7，调试用）")
    args = parser.parse_args()

    run(args.source, args.execute, args.refresh_docs, args.step)


if __name__ == "__main__":
    main()
