"""
确定性代码渲染模块 - WebSocket 版
根据 AI 生成的测试场景 JSON + Jinja2 模板，生成 pytest 测试代码
不需要 AI
"""

import json
import os
import re
from datetime import datetime
from jinja2 import Environment, FileSystemLoader


TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_generated_testcases")


def render_ws_test_code(
    scenario_name: str,
    scenarios: dict,
) -> str:
    """
    将 AI 生成的测试场景渲染为 pytest 代码

    : scenario_name: 场景名称（用于生成类名和文件名）
    : scenarios: ai_generator 返回的测试场景 JSON
    : 生成的 pytest 代码字符串
    """
    env = Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        keep_trailing_newline=True,
        extensions=["jinja2.ext.do"],
    )
    env.filters["to_pretty_json"] = _to_pretty_json

    template = env.get_template("test_ws_interface.tpl")

    class_name = _to_class_name(scenario_name)
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    code = template.render(
        scenario_name=scenario_name,
        class_name=class_name,
        generated_time=generated_time,
        interfaces=scenarios.get("interfaces", []),
    )

    return code


def save_test_file(scenario_name: str, code: str) -> str:
    """将生成的代码保存到 ai_generated_testcases/<workflow_name>/ 目录"""
    workflow_dir = os.path.join(OUTPUT_DIR, scenario_name)
    os.makedirs(workflow_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", scenario_name)
    file_name = f"test_{safe_name}.py"
    file_path = os.path.join(workflow_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    return file_path


def render_and_save_workflow(scenario_name: str, workflow: dict, scenarios: dict = None) -> str:
    """渲染工作流测试（happy path + 变异测试）并保存"""
    code = render_ws_workflow_test(scenario_name, workflow, scenarios)
    workflow_dir = os.path.join(OUTPUT_DIR, scenario_name)
    os.makedirs(workflow_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_]", "_", scenario_name)
    file_name = f"test_{safe_name}_workflow.py"
    file_path = os.path.join(workflow_dir, file_name)

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(code)

    return file_path


def render_ws_workflow_test(scenario_name: str, workflow: dict, scenarios: dict = None) -> str:
    """
    根据 workflow.json + scenarios.json 渲染工作流测试（happy path + 变异测试）

    :param scenario_name: 场景名称
    :param workflow: workflow.json 数据（调用顺序、状态依赖）
    :param scenarios: scenarios.json 数据（变异场景、预期结果）
    :return: 生成的 pytest 代码字符串
    """
    class_name = _to_class_name(scenario_name)
    generated_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    interfaces = sorted(workflow.get("interfaces", []), key=lambda x: x.get("seq", 0))

    # 构建 workflow seq -> scenarios 的映射
    scenario_map = _build_scenario_map(interfaces, scenarios) if scenarios else {}

    mutation_count = sum(
        len([s for s in ifs.get("test_scenarios", [])
             if s.get("category") not in ("normal", "invalid_func")])
        for ifs in scenario_map.values()
    )

    lines = [
        '"""',
        "AI 自动生成的 WebSocket 工作流测试用例",
        f"场景: {scenario_name}",
        f"生成时间: {generated_time}",
        "",
        "包含:",
        "  - test_workflow_happy_path: 按工作流顺序链式调用所有接口",
        f"  - {mutation_count} 个变异测试: 在工作流上下文中注入异常参数",
        '"""',
        "",
        "import pytest",
        "import sys",
        "import os",
        "",
        "sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))",
        "",
        "from core.request_invoker import send_request",
        "",
        "",
        f"class {class_name}:",
        "",
    ]

    # 1. 生成 _run_happy_path_to 辅助方法
    lines.extend(_gen_happy_path_helper(interfaces))
    lines.append("")

    # 2. 生成 happy path 测试
    max_seq = interfaces[-1]["seq"] if interfaces else 0
    lines.append("    def test_workflow_happy_path(self, ws_client):")
    lines.append('        """按工作流顺序执行所有接口，验证链式调用"""')
    lines.append(f"        state = self._run_happy_path_to(ws_client, {max_seq + 1})")
    lines.append(f"        assert state, '工作流执行完成但状态为空'")
    lines.append("")

    # 3. 生成变异测试
    if scenario_map:
        lines.extend(_gen_mutation_tests(interfaces, scenario_map))

    lines.append("")
    lines.append("if __name__ == '__main__':")
    lines.append("    pytest.main([__file__, '-v', '--tb=short'])")
    lines.append("")

    return "\n".join(lines)





# ─────────────────── 内部辅助函数 ───────────────────


def _build_scenario_map(interfaces: list, scenarios: dict) -> dict:
    """
    建立 workflow seq -> scenario interface 的映射。
    对于重复 func 名，按出现顺序依次匹配。
    """
    func_groups = {}
    for siface in scenarios.get("interfaces", []):
        func = siface["func"]
        func_groups.setdefault(func, []).append(siface)

    used_index = {}
    result = {}

    for iface in interfaces:
        seq = iface["seq"]
        func = iface["func"]
        group = func_groups.get(func, [])
        idx = used_index.get(func, 0)

        if idx < len(group):
            result[seq] = group[idx]
            used_index[func] = idx + 1

    return result


def _gen_happy_path_helper(interfaces: list) -> list:
    """生成 _run_happy_path_to 辅助方法代码"""
    lines = [
        "    def _run_happy_path_to(self, ws_client, target_seq):",
        '        """执行工作流步骤 1 到 target_seq-1，返回 state dict"""',
        "        state = {}",
        "",
    ]

    for iface in interfaces:
        seq = iface["seq"]
        func = iface["func"]
        desc = iface.get("desc", func)
        args_detail = iface.get("args_detail", [])
        response_usage = iface.get("response_usage")

        lines.append(f"        # Step {seq}: {func}")

        args_parts = _build_args_expr(args_detail)
        lines.append(f"        resp_{seq} = send_request(")
        lines.append(f"            ws_client,")
        lines.append(f'            "{func}",')
        lines.append(f"            [{', '.join(args_parts)}],")
        lines.append(f'            "{desc}",')
        lines.append(f"        )")
        lines.append(f'        assert resp_{seq} is not None, f"Step {seq} {func} 返回为空"')
        lines.append(f'        assert resp_{seq}.get("success") == True, f"Step {seq} {func} 失败: {{resp_{seq}}}"')

        if response_usage:
            captured_by = response_usage.get("captured_by", "")
            lines.append(f'        if resp_{seq}.get("ret"):')
            lines.append(f'            state["{captured_by}"] = resp_{seq}["ret"][0]')

        lines.append(f"        if target_seq <= {seq}:")
        lines.append(f"            return state")
        lines.append("")

    lines.append("        return state")
    return lines


def _gen_mutation_tests(interfaces: list, scenario_map: dict) -> list:
    """为每个接口的每个变异场景生成测试方法"""
    lines = []
    seen_method_names = set()

    for iface in interfaces:
        seq = iface["seq"]
        func = iface["func"]
        desc = iface.get("desc", func)

        if seq not in scenario_map:
            continue

        scenario_iface = scenario_map[seq]
        test_scenarios = scenario_iface.get("test_scenarios", [])

        for ts in test_scenarios:
            category = ts.get("category", "")

            # 跳过 normal 和 invalid_func
            if category in ("normal", "invalid_func"):
                continue

            name = ts.get("name", f"step{seq}_{category}")
            ts_desc = ts.get("description", "")
            args = ts.get("args", [])
            expected = ts.get("expected", {})
            should_success = expected.get("should_success", False)

            # 生成唯一方法名：用 seq 前缀避免重名
            raw_name = re.sub(r"[^a-zA-Z0-9_]", "_", name)
            if raw_name.startswith("test_"):
                raw_name = raw_name[5:]
            method_name = f"test_step{seq}_{raw_name}"

            if method_name in seen_method_names:
                method_name = f"{method_name}_seq{seq}"
            seen_method_names.add(method_name)

            lines.append(f"    def {method_name}(self, ws_client):")
            lines.append(f'        """Step {seq} 变异测试 [{category}]: {ts_desc}"""')

            # 前置：跑 happy path 到当前步骤之前
            if seq > 1:
                lines.append(f"        state = self._run_happy_path_to(ws_client, {seq})")

            # 发送变异请求
            args_repr = ", ".join(_repr_arg(a) for a in args)
            lines.append(f"        resp = send_request(")
            lines.append(f"            ws_client,")
            lines.append(f'            "{func}",')
            lines.append(f"            [{args_repr}],")
            lines.append(f'            "{desc} [{category}]",')
            lines.append(f"        )")

            # 断言
            lines.append(f"        assert resp is not None, '接口返回为空'")
            if should_success:
                lines.append(f'        assert resp.get("success") == True, f"预期成功但失败: {{resp}}"')
            else:
                lines.append(f'        assert resp.get("success") == False, f"预期失败但成功: {{resp}}"')

            lines.append("")

    return lines


def _build_args_expr(args_detail: list) -> list[str]:
    """根据 args_detail 构建参数表达式列表"""
    parts = []
    for ad in args_detail:
        source = ad.get("source", "literal")
        value = ad.get("value")

        if source.startswith("state:"):
            var_name = source[len("state:"):].strip()
            parts.append(f'state.get("{var_name}", -1)')
        else:
            parts.append(repr(value))

    return parts


def _repr_arg(arg) -> str:
    """将 JSON 参数转为 Python 表达式"""
    if arg is None:
        return "None"
    if isinstance(arg, list):
        inner = ", ".join(_repr_arg(a) for a in arg)
        return f"[{inner}]"
    return repr(arg)


def _to_class_name(name: str) -> str:
    """转为合法的 Python 类名"""
    parts = re.split(r"[/,_\-\.]", name)
    parts = [p for p in parts if p]
    return "Test" + "".join(p.capitalize() for p in parts)


def _to_pretty_json(value) -> str:
    """Jinja2 过滤器：将值转为格式化的 JSON 字符串"""
    return json.dumps(value, ensure_ascii=False, indent=8).replace("null", "None")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        with open(json_file, "r", encoding="utf-8") as f:
            scenarios = json.load(f)

        scenario_name = os.path.splitext(os.path.basename(json_file))[0]
        code = render_ws_test_code(scenario_name, scenarios)
        file_path = save_test_file(scenario_name, code)
        print(f"测试代码已生成: {file_path}")
    else:
        print("用法: python code_renderer.py <scenarios_json_file>")
