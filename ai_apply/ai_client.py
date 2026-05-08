"""
AI 统一客户端 - 使用 OpenAI SDK + Tools 实现结构化输出

替代原先 3 个模块各自 requests.post() + _extract_json() 的做法，
通过官方 SDK + tools 让 LLM 返回结构化 JSON，无需从自由文本中提取。

用法:
    from ai_client import AIClient, WORKFLOW_TOOL, SEMANTICS_TOOL, SCENARIOS_TOOL

    client = AIClient()

    result = client.call(
        system_prompt=SYSTEM_PROMPT,
        user_message=user_message,
        tool=WORKFLOW_TOOL,
    )
    # result 已经是解析好的 dict，不需要 _extract_json()
"""

import json
import os
import re
import yaml
from openai import OpenAI


def load_llm_config(config_path: str = None) -> dict:
    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "config", "llm_config.yaml"
        )
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


# ===================== Tool Schema 定义 =====================

SEMANTICS_TOOL = {
    "type": "function",
    "function": {
        "name": "output_semantics",
        "description": "输出接口语义分析结果，包括业务含义、参数约束、预期响应等",
        "parameters": {
            "type": "object",
            "properties": {
                "interfaces": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "func": {"type": "string", "description": "接口函数名"},
                            "seq": {"type": "integer"},
                            "business_meaning": {"type": "string"},
                            "interface_type": {"type": "string", "enum": ["query", "command"]},
                            "params": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "index": {"type": "integer"},
                                        "params_name": {"type": "string"},
                                        "type": {"type": "string"},
                                        "required": {"type": "integer", "description": "0=必填, 1=非必填"},
                                        "valid_range": {"type": "string"},
                                        "boundary_values": {"type": "array", "items": {"type": "string"}},
                                        "enum_values": {"type": "array", "items": {"type": "string"}},
                                        "special_char_limit": {"type": "string"},
                                        "depends_on": {"type": "string"},
                                    },
                                },
                            },
                            "expected_response": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "string"},
                                    "ret": {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string"},
                                            "description": {"type": "string"},
                                            "structure": {"type": "string"},
                                            "example": {"type": "string"},
                                        },
                                    },
                                    "error": {"type": "string"},
                                    "abnormal_responses": {
                                        "type": "array",
                                        "items": {
                                            "type": "object",
                                            "properties": {
                                                "scenario": {"type": "string"},
                                                "success": {"type": "boolean"},
                                                "error": {"type": "string"},
                                            },
                                        },
                                    },
                                },
                            },
                            "upstream": {
                                "type": "object",
                                "properties": {
                                    "must_call_before": {"type": "array", "items": {"type": "string"}},
                                    "data_flow": {"type": "array", "items": {"type": "object"}},
                                    "system_state": {"type": "string"},
                                },
                            },
                            "downstream": {
                                "type": "object",
                                "properties": {
                                    "produces": {"type": "array", "items": {"type": "object"}},
                                    "state_change": {"type": "string"},
                                },
                            },
                            "business_rules": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["func", "seq"],
                    },
                },
            },
            "required": ["interfaces"],
        },
    },
}

SCENARIOS_TOOL = {
    "type": "function",
    "function": {
        "name": "output_test_scenarios",
        "description": "输出测试场景生成结果，包括正常/边界/异常等测试用例",
        "parameters": {
            "type": "object",
            "properties": {
                "interfaces": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "func": {"type": "string"},
                            "description": {"type": "string"},
                            "test_scenarios": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string", "description": "场景英文名，用作函数名"},
                                        "description": {"type": "string", "description": "场景描述（中文）"},
                                        "category": {
                                            "type": "string",
                                            "enum": [
                                                "normal", "boundary", "wrong_arg_type",
                                                "missing_args", "violation", "invalid_func", "null_args",
                                            ],
                                        },
                                        "priority": {"type": "integer"},
                                        "args": {"type": "array", "items": {"type": "object"}, "description": "参数列表"},
                                        "expected": {
                                            "type": "object",
                                            "properties": {
                                                "should_success": {"type": "boolean"},
                                                "assertions": {"type": "array", "items": {"type": "string"}},
                                            },
                                        },
                                    },
                                    "required": ["name", "category", "args", "expected"],
                                },
                            },
                        },
                        "required": ["func", "test_scenarios"],
                    },
                },
            },
            "required": ["interfaces"],
        },
    },
}


# ===================== 客户端 =====================

class AIClient:
    """AI 统一客户端 - 封装 OpenAI SDK + Tools 调用（结构化输出）"""

    def __init__(self, config: dict = None):
        if config is None:
            config = load_llm_config()

        # 从配置中提取 base_url（api_url 去掉末尾 /chat/completions）
        api_url = config["api_url"]
        base_url = api_url.replace("/chat/completions", "").rstrip("/")

        self.client = OpenAI(
            api_key=config["api_key"],
            base_url=base_url,
        )
        self.model = config["model"]
        self.default_temperature = config.get("temperature", 0.3)
        self.max_tokens = config.get("max_tokens", 4096)

    def call(
        self,
        system_prompt: str,
        user_message: str,
        tool: dict,
        temperature: float = None,
    ) -> dict:
        """
        调用 LLM + Tool，返回结构化 JSON。

        Args:
            system_prompt: 系统提示词（各模块自己定义）
            user_message: 用户消息（各模块自行拼接）
            tool: Tool schema（WORKFLOW_TOOL / SEMANTICS_TOOL / SCENARIOS_TOOL）
            temperature: 可选覆盖温度

        Returns:
            解析好的 dict，直接可用，不需要 _extract_json()
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            tools=[tool],
            tool_choice={"type": "function", "function": {"name": tool["function"]["name"]}},
            temperature=temperature if temperature is not None else self.default_temperature,
            max_tokens=self.max_tokens,
        )

        message = response.choices[0].message

        # LLM 通过 tool_calls 返回结构化数据
        if message.tool_calls:
            return json.loads(message.tool_calls[0].function.arguments)

        # 兜底：模型不支持 tools 时，从自由文本提取 JSON
        if message.content:
            return _extract_json(message.content)

        raise ValueError("LLM 未返回有效内容")


def _extract_json(text: str) -> dict:
    """兜底：从自由文本中提取 JSON（兼容不支持 tools 的模型）"""
    text = text.strip()
    if "```" in text:
        match = re.search(r"```(?:json)?\s*\n?(.*?)```", text, re.DOTALL)
        if match:
            return json.loads(match.group(1).strip())

    brace_count = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if brace_count == 0:
                start = i
            brace_count += 1
        elif ch == "}":
            brace_count -= 1
            if brace_count == 0 and start >= 0:
                return json.loads(text[start : i + 1])

    return json.loads(text)


def call_batch(
    self,
    system_prompt: str,
    batches: list,
    tool: dict,
    temperature: float = None,
) -> list:
    """
    批量调用（分批处理大量接口时使用）。

    Args:
        batches: 每个元素是一批接口的 user_message

    Returns:
        list[dict]，每批的解析结果
    """
    results = []
    for i, user_message in enumerate(batches):
        print(f"  批次 {i + 1}/{len(batches)}...")
        results.append(self.call(system_prompt, user_message, tool, temperature))
    return results