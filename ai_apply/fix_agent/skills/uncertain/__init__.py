"""
AI 辅助兜底 skill

处理 uncertain 类型错误，复用原 propose_fix 的逻辑和 FIX_SYSTEM_PROMPT。
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

UNCERTAIN_FIX_PROMPT = """\
你是一个自动化测试修复工程师。

当前错误分类为"不确定"，请根据以下信息尝试提出修复方案。
如果无法确定修复方案，选择 escalate_human。

## 修复原则
1. 只修改导致失败的字段
2. 利用语义约束信息确定正确参数值
3. 不确定时选择 escalate_human 而不是盲目修改
"""


class UncertainSkill(BaseFixSkill):
    category = "uncertain"
    name = "uncertain_fixer"

    def execute(self, state: dict) -> dict:
        from ai_client import AIClient
        from ..schemas import FIX_PROPOSAL_TOOL

        user_message = self._build_prompt(state)

        client = AIClient()
        try:
            result = client.call(
                system_prompt=UNCERTAIN_FIX_PROMPT,
                user_message=user_message,
                tool=FIX_PROPOSAL_TOOL,
            )
        except Exception as e:
            logger.error("AI uncertain 修复失败: %s", e)
            return {
                "fix_action": "escalate_human",
                "fix_details": [],
                "fix_proposal_confidence": 0.0,
            }

        return {
            "fix_action": result.get("fix_action", "escalate_human"),
            "fix_details": result.get("fix_details", []),
            "fix_proposal_confidence": result.get("confidence", 0.3),
        }

    def _build_prompt(self, state: dict) -> str:
        parts = []

        parts.append("## 错误信息\n")
        parts.append(f"根因: {state.get('root_cause', '未知')}")
        for ft in state.get("failed_tests", []):
            parts.append(f"- {ft['test_name']}: {ft['error_message']}")
        parts.append("")

        affected = state.get("affected_interfaces", [])
        parts.append("## 当前场景数据\n")
        for iface in state.get("scenarios", {}).get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            parts.append(f"### {iface['func']}")
            parts.append("```json")
            parts.append(json.dumps(iface.get("test_scenarios", []), ensure_ascii=False, indent=2))
            parts.append("```")
            parts.append("")

        parts.append("## 语义约束\n")
        for iface in state.get("semantics", {}).get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            parts.append(f"### {iface['func']}")
            parts.append(f"参数: {json.dumps(iface.get('params', []), ensure_ascii=False)}")
            parts.append("")

        history = state.get("history", [])
        if history:
            parts.append("## 之前的修复尝试（请勿重复）\n")
            for h in history:
                parts.append(f"- 第 {h['retry']} 次: {h['category']} → {h['action']} → {h['result']}")

        return "\n".join(parts)
