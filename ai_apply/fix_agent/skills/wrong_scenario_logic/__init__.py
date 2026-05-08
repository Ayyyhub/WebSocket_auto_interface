"""
AI 辅助修复 wrong_scenario_logic 错误

处理测试场景的预期结果写反了的情况（如异常场景期望 success=True）。
需要 AI 理解业务语义来判断预期是否合理。
"""

import json
import logging
import sys
import os

from ..base import BaseFixSkill

_AI_APPLY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
if _AI_APPLY_DIR not in sys.path:
    sys.path.insert(0, os.path.normpath(_AI_APPLY_DIR))

logger = logging.getLogger("fix_agent.skills")

LOGIC_FIX_PROMPT = """\
你是一个自动化测试逻辑审核专家。

你的任务是检查测试场景的 category 与 expected.should_success 是否矛盾。

## 规则
- normal 场景通常 should_success = true
- boundary 场景：合法边界值应 success=true，越界值应 success=false
- wrong_arg_type 场景应 should_success = false
- missing_args 场景应 should_success = false
- violation 场景应 should_success = false
- null_args 场景：必填参数传 null 应 success=false
- invalid_func 场景应 should_success = false

请根据语义分析中的 abnormal_responses 和 business_rules 来判断。
如果发现矛盾，提出修改 expected.should_success 或 expected.assertions 的方案。
"""


class WrongScenarioLogicSkill(BaseFixSkill):
    category = "wrong_scenario_logic"
    name = "wrong_scenario_logic_fixer"

    def execute(self, state: dict) -> dict:
        from ai_client import AIClient
        from schemas import FIX_PROPOSAL_TOOL

        user_message = self._build_prompt(state)

        client = AIClient()
        try:
            result = client.call(
                system_prompt=LOGIC_FIX_PROMPT,
                user_message=user_message,
                tool=FIX_PROPOSAL_TOOL,
            )
        except Exception as e:
            logger.error("AI scenario logic 修复失败: %s", e)
            return {
                "fix_action": "escalate_human",
                "fix_details": [],
                "fix_proposal_confidence": 0.0,
            }

        return {
            "fix_action": result.get("fix_action", "escalate_human"),
            "fix_details": result.get("fix_details", []),
            "fix_proposal_confidence": result.get("confidence", 0.5),
        }

    def _build_prompt(self, state: dict) -> str:
        parts = []

        parts.append("## 错误分析\n")
        parts.append(f"根因: {state.get('root_cause', '')}")
        for ft in state.get("failed_tests", []):
            parts.append(f"- {ft['test_name']}: {ft['error_message']}")
        parts.append("")

        affected = state.get("affected_interfaces", [])
        parts.append("## 场景逻辑检查\n")
        for iface, scenario, _ in self._extract_affected_scenarios(state):
            if affected and iface["func"] not in affected:
                continue
            parts.append(
                f"- **{iface['func']}** / {scenario['name']}:\n"
                f"  category={scenario.get('category')}, "
                f"expected.should_success={scenario.get('expected', {}).get('should_success')}"
            )
        parts.append("")

        parts.append("## 语义预期响应\n")
        for iface in state.get("semantics", {}).get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            er = iface.get("expected_response", {})
            if er.get("abnormal_responses"):
                parts.append(f"### {iface['func']} 异常响应:")
                for ab in er["abnormal_responses"]:
                    parts.append(f"  - {ab.get('scenario')}: success={ab.get('success')}, error=\"{ab.get('error')}\"")
            if iface.get("business_rules"):
                parts.append(f"业务规则: {'; '.join(iface['business_rules'])}")
            parts.append("")

        return "\n".join(parts)
