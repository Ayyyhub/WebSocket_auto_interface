"""
测试场景设计模块（LLM）

只设计测试方向（normal/boundary/violation...），
具体参数值由 data_builder.TestDataBuilder 根据语义约束自动生成。
"""

import json
import os
from typing import Optional

from ai_client import AIClient, SCENARIOS_TOOL


SYSTEM_PROMPT = """你是一个专业的 WebSocket 接口测试工程师。

你会收到：
1. 接口的原始定义（func 名称、参数示例、描述）
2. 接口的业务语义分析（业务含义、参数约束、前置条件、业务规则）

你只需要设计**测试方向**，不需要生成具体的测试数据。
具体参数值会由代码根据参数约束自动计算。

对每个接口，设计以下维度的测试场景：

1. **normal**: 正常场景（需要满足所有前置条件和参数约束）
2. **boundary**: 基于参数约束的边界值测试（需要指出对哪个参数做边界测试）
3. **wrong_arg_type**: 参数类型错误（需要指出哪个参数传什么错误类型）
4. **missing_args**: 缺少必要参数（需要指出缺少哪个参数）
5. **violation**: 违反业务规则的场景（如未满足前置条件、传无效枚举值）
6. **invalid_func**: 不存在的 func 名称
7. **null_args**: 参数传 null/None（需要指出哪个参数）

注意：
- 不是每个接口都需要所有维度，根据实际情况选择
- violation 场景要基于业务规则设计，不是随便写
- 函数名格式：test_<func简称>_<category>，确保全局唯一

严格按以下 JSON 格式输出：
{
  "interfaces": [
    {
      "func": "接口名称",
      "description": "接口描述",
      "test_scenarios": [
        {
          "name": "场景名称（英文，用作函数名）",
          "description": "场景描述（中文）",
          "category": "normal|boundary|wrong_arg_type|missing_args|violation|invalid_func|null_args",
          "priority": 1,
          "target_params": {
            "param_hint": "如：对控制器索引做边界测试 / 缺少场景文件参数 / 模型路径传int"
          },
          "expected": {
            "should_success": true/false,
            "assertions": ["断言描述1", "断言描述2"]
          }
        }
      ]
    }
  ]
}"""


def generate_test_scenarios(
    interfaces_text: str,
    semantics_text: str = "",
    config: Optional[dict] = None,
) -> dict:
    """
    调用大模型设计测试场景方向（不含具体测试数据）

    :param interfaces_text: 原始接口定义文本
    :param semantics_text: 语义分析结果文本
    :param config: 大模型配置
    :return: 测试场景 JSON（不含 args）
    """
    user_content = f"以下是接口的原始定义：\n\n{interfaces_text}\n"
    if semantics_text:
        user_content += f"以下是接口的业务语义分析：\n\n{semantics_text}\n"
    user_content += "请基于以上信息设计测试场景方向，不需要生成具体测试数据。"

    client = AIClient(config=config)
    return client.call(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_content,
        tool=SCENARIOS_TOOL,
    )


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.dirname(__file__))

    service_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Service")

    if len(sys.argv) > 1:
        source = sys.argv[1]
        if source.endswith(".py"):
            from flattening_parser import parse_service_file
            interfaces = parse_service_file(source)
        else:
            from flattening_parser import format_for_ai, parse_service_dir
            interfaces = parse_service_dir(source)
    else:
        from flattening_parser import format_for_ai, parse_service_dir
        interfaces = parse_service_dir(service_dir)

    interfaces = interfaces[:3]
    api_text = format_for_ai(interfaces)
    print("=" * 60)
    print("接口信息：")
    print(api_text)
    print("=" * 60)
    print("正在调用大模型设计测试场景...")

    result = generate_test_scenarios(api_text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
