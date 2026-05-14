"""
AI 语义解析模块（第 1 次 AI 调用）

输入：workflow.json（接口关系图）+ raw_interfaces + 钉钉文档（可选）
输出：semantics.json（业务语义 + 参数约束）

专注分析：
- 每个接口的业务含义
- 每个参数的数据约束（类型、范围、枚举值）
- 预期响应结构
- 查询型/操作型分类
不分析：接口之间的依赖关系（已由 workflow_ai_analyzer 完成）
"""

import json
import os
from typing import Optional

from ai_client import AIClient, SEMANTICS_TOOL


SYSTEM_PROMPT = """你是一个资深的机器人仿真平台接口分析专家。

你将收到：
1. 一个工作流的接口关系图（workflow.json，已标注接口之间的依赖和数据流向）
2. 接口的原始调用信息（func 名、参数值、描述）

接口之间的关系已经分析好了，你只需要专注每个接口的**业务语义和参数约束**。

分析要求：

1. **业务含义**：这个接口在做什么？在工作流中处于什么位置？
2. **接口类型**：查询型（只读，不改数据）还是操作型（会改变系统状态）？
3. **参数约束**：对每个参数分析：
   - 参数数据类型
   - 是否必填
   - 枚举值（如有）
   - 有效范围（如：索引 0-5、坐标值 -1000~1000）、边界值
   - 特殊字符限制
   - 与其他参数的关联关系
4. **预期结果**：响应字段的必填性、数据类型、枚举值 / 格式规则；正常 / 异常场景对应的错误提示文案
5. **业务规则**：重复调用的行为、幂等性、异常处理建议

严格按以下 JSON 格式输出：
{
  "interfaces": [
    {
      "func": "接口名",
      "seq": 1,
      "business_meaning": "业务含义描述",
      "interface_type": "query | command",
      "params": [
        {
          "index": 0,默认从0开始，若有多个参数时索引增加
          "params_name": "推断的参数名",
          "type": "参数数据类型（如 int, str, list, float）",
          "required": 0(true，必填)，1(false，非必填)
          "valid_range": "有效范围描述（如 0-5, -1000~1000）",
          "boundary_values": ["边界值示例，如 0, -1, 最大值"],
          "enum_values": ["枚举值（如有）"],
          "special_char_limit": "特殊字符限制（如适用）",
          "depends_on": "依赖其他接口的哪个返回值（如有）"
        },
      ],
      "expected_response": {
        "success": "bool, 必填, 表示请求是否成功",
        "ret": {
          "type": "ret 的数据类型（如 list[int], list[str], list[dict], 空列表[]）",
          "description": "ret 内容的业务含义",
          "structure": "ret 内部结构描述（如 ret[0] 为对象ID/int）",
          "example": "正常返回示例值"
        },
        "error": "str, 失败时的错误信息, 成功时通常为空或不存在",
        "abnormal_responses": [
          {
            "scenario": "异常场景描述（如参数缺失、参数越界、前置条件未满足）",
            "success": false,
            "error": "预期的错误提示文案"
          }
        ]
      },
      "upstream": {
        "must_call_before": ["必须先调用的上游接口 func 名"],
        "data_flow": [
          {"from_func": "上游接口名", "from_field": "ret[0]", "to_param_index": 0, "desc": "数据流向说明"}
        ],
        "system_state": "调用前系统必须处于什么状态"
      },
      "downstream": {
        "produces": [
          {"field": "ret[0]", "type": "int", "consumed_by": "下游接口名", "as_param_index": 0, "desc": "数据流向说明"}
        ],
        "state_change": "调用成功后改变了系统什么状态"
      },
      "business_rules": ["业务规则1", "业务规则2"]
    }
  ]
}"""


def parse_semantics(interfaces_text: str, workflow_text: str = "", config: Optional[dict] = None) -> dict:
    """
    调用大模型解析接口语义和数据约束

    :param interfaces_text: 原始接口列表文本
    :param workflow_text: workflow.json 格式化后的关系图文本（可选，提供依赖上下文）
    :param config: 大模型配置
    :return: 语义分析结果 JSON
    """
    # 构造用户消息：如果有 workflow 关系图，一并提供
    if workflow_text:
        user_message = (
            f"## 接口关系图（已分析好的依赖关系）\n{workflow_text}\n\n"
            f"## 原始接口调用信息\n{interfaces_text}\n\n"
            f"请基于以上信息分析每个接口的业务语义和参数约束。"
        )
    else:
        user_message = f"请分析以下接口的业务语义和数据约束：\n\n{interfaces_text}"

    client = AIClient(config=config)
    temperature = config.get("temperature", 0.2) if config else 0.2
    return client.call(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tool=SEMANTICS_TOOL,
        temperature=temperature,
    )


def format_semantics_for_generator(semantics: dict) -> str:
    """
    将语义分析结果格式化为文本，供 ai_generator 使用
    这就是"带业务理解的接口文档"
    """
    lines = []
    for i, iface in enumerate(semantics.get("interfaces", []), 1):
        if not isinstance(iface, dict):
            continue
        lines.append(f"### 接口 {i}: {iface['func']}")
        lines.append(f"业务含义: {iface.get('business_meaning', '')}")

        if iface.get("params"):
            lines.append("参数约束:")
            for p in iface["params"]:
                if not isinstance(p, dict):
                    continue
                required_mark = "必填" if p.get("required") else "选填"
                constraint_parts = [f"业务类型={p.get('business_type', '未知')}"]
                if p.get("valid_range"):
                    constraint_parts.append(f"有效范围={p['valid_range']}")
                if p.get("enum_values"):
                    constraint_parts.append(f"枚举值={p['enum_values']}")
                if p.get("depends_on"):
                    constraint_parts.append(f"依赖={p['depends_on']}")
                lines.append(f"  args[{p.get('index', '?')}]: {required_mark}, {', '.join(constraint_parts)}")

        if iface.get("expected_response"):
            er = iface["expected_response"]
            lines.append("预期结果:")
            lines.append(f"  success: {er.get('success', '未知')}")
            if er.get("ret"):
                ret_info = er["ret"]
                lines.append(f"  ret类型: {ret_info.get('type', '未知')}")
                lines.append(f"  ret含义: {ret_info.get('description', '')}")
                if ret_info.get("structure"):
                    lines.append(f"  ret结构: {ret_info['structure']}")
                if ret_info.get("example"):
                    lines.append(f"  ret示例: {ret_info['example']}")
            if er.get("error"):
                lines.append(f"  error: {er['error']}")
            if er.get("abnormal_responses"):
                lines.append("  异常响应:")
                for ab in er["abnormal_responses"]:
                    lines.append(f"    - {ab.get('scenario', '')}: error=\"{ab.get('error', '')}\"")

        if iface.get("upstream"):
            up = iface["upstream"]
            lines.append("上游依赖:")
            if up.get("must_call_before"):
                lines.append(f"  必先调用: {', '.join(up['must_call_before'])}")
            if up.get("data_flow"):
                lines.append("  数据流入:")
                for df in up["data_flow"]:
                    lines.append(f"    ← {df.get('from_func', '?')}.{df.get('from_field', '?')} → args[{df.get('to_param_index', '?')}]: {df.get('desc', '')}")
            if up.get("system_state"):
                lines.append(f"  系统状态: {up['system_state']}")

        if iface.get("downstream"):
            down = iface["downstream"]
            lines.append("下游消费:")
            if down.get("produces"):
                lines.append("  数据流出:")
                for prod in down["produces"]:
                    lines.append(f"    → {prod.get('field', '?')} ({prod.get('type', '?')}) → {prod.get('consumed_by', '?')}.args[{prod.get('as_param_index', '?')}]: {prod.get('desc', '')}")
            if down.get("state_change"):
                lines.append(f"  状态变更: {down['state_change']}")
        if iface.get("business_rules"):
            lines.append(f"业务规则: {'; '.join(iface['business_rules'])}")

        lines.append("")

    return "\n".join(lines)




if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))
    from flattening_parser import format_for_ai, parse_service_file, parse_service_dir

    service_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Service")

    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.endswith(".py"):
            interfaces = parse_service_file(source)
        else:
            interfaces = parse_service_dir(os.path.join(service_dir, f"{source}_chain.py"))
    else:
        interfaces = parse_service_dir(service_dir)

    api_text = format_for_ai(interfaces[:5])

    print("=" * 60)
    print("接口原始信息：")
    print(api_text)
    print("=" * 60)
    print("正在调用大模型解析业务语义...")

    semantics = parse_semantics(api_text)
    print(json.dumps(semantics, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("格式化后的语义分析（供用例生成使用）：")
    print(format_semantics_for_generator(semantics))
