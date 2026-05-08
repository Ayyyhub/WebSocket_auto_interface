"""
确定性文档解析模块 - WebSocket 版
从 Service 层 Python 代码中提取接口结构化信息
不需要 AI，纯代码解析
"""

import ast
import json
import os
import re
from typing import Optional


def parse_service_file(file_path: str) -> list[dict]:
    """
    解析 Service 层 Python 文件，提取所有 send_request 调用的接口信息
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source = f.read()

    interfaces = []
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "send_request"):
            continue

        # send_request(ws_client, "func_name", [args], "desc")
        args = node.args
        if len(args) < 4:
            continue

        func_name = _extract_str(args[1])
        func_args = _extract_args(args[2])
        desc = _extract_str(args[3])

        if not func_name:
            continue

        interfaces.append({
            "func": func_name,
            "args_example": func_args,
            "description": desc,
            "source_file": os.path.basename(file_path),
        })

    return interfaces


def parse_service_dir(dir_path: str) -> list[dict]:
    """解析 Service 目录下所有文件"""
    all_interfaces = []
    seen = set()

    for filename in sorted(os.listdir(dir_path)):
        if not filename.endswith("_chain.py"):
            continue
        filepath = os.path.join(dir_path, filename)
        interfaces = parse_service_file(filepath)
        for iface in interfaces:
            # 去重：同一个 func 只保留第一次出现的定义
            key = iface["func"]
            if key not in seen:
                seen.add(key)
                all_interfaces.append(iface)

    return all_interfaces


def format_for_ai(interfaces: list[dict]) -> str:
    """
    将接口列表格式化为大模型可读的文本
    """
    lines = []
    for i, iface in enumerate(interfaces, 1):
        lines.append(f"### 接口 {i}: {iface['func']}")
        lines.append(f"描述: {iface['description']}")
        lines.append(f"来源: {iface.get('source_file', '')}")
        lines.append(f"参数示例: {json.dumps(iface['args_example'], ensure_ascii=False)}")

        # 从描述和参数推断约束
        args = iface["args_example"]
        if args:
            lines.append("参数说明:")
            for j, arg in enumerate(args):
                arg_type = type(arg).__name__
                if isinstance(arg, list):
                    arg_type = f"list[{len(arg)}项]"
                lines.append(f"  - args[{j}]: 类型={arg_type}, 示例值={json.dumps(arg, ensure_ascii=False)}")

        lines.append("")

    return "\n".join(lines)


def _extract_str(node) -> Optional[str]:
    """从 AST 节点提取字符串值"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_args(node) -> list:
    """从 AST 节点提取 args 列表"""
    if isinstance(node, ast.List):
        return [_eval_const(elt) for elt in node.elts]
    return []


def _eval_const(node):
    """递归求值 AST 常量节点"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_eval_const(elt) for elt in node.elts]
    if isinstance(node, ast.Dict):
        keys = [_eval_const(k) for k in node.keys]
        values = [_eval_const(v) for v in node.values]
        return dict(zip(keys, values))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_const(node.operand)
    if isinstance(node, ast.Name):
        return f"<变量: {node.id}>"
    return f"<表达式>"


if __name__ == "__main__":
    import sys

    service_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Service")

    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.endswith(".py"):
            interfaces = parse_service_file(source)
        else:
            interfaces = parse_service_dir(source)
    else:
        interfaces = parse_service_dir(service_dir)

    print(f"共解析到 {len(interfaces)} 个 WebSocket 接口\n")
    print(format_for_ai(interfaces))
