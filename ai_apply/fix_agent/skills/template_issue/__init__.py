"""
AI 辅助修复 template_issue 错误

处理渲染模板生成的代码有语法错误、import 缺失等问题。
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

TEMPLATE_FIX_PROMPT = """\
你是一个 Jinja2 模板和 pytest 代码修复专家。

当前生成的测试代码存在问题（语法错误、import 缺失等）。
这类问题通常需要修改测试场景数据（scenarios.json）来避免模板渲染出错误代码，
而不是直接修改生成的 .py 文件。

请检查失败场景的 args 和 expected 数据是否有导致模板渲染异常的特殊值。
如果确认是模板 bug 而非数据问题，选择 escalate_human。
"""


class TemplateIssueSkill(BaseFixSkill):
    category = "template_issue"
    name = "template_issue_fixer"

    def execute(self, state: dict) -> dict:
        from ai_client import AIClient
        from ..schemas import FIX_PROPOSAL_TOOL

        user_parts = []
        user_parts.append("## 错误分析\n")
        user_parts.append(f"根因: {state.get('root_cause', '')}")
        for ft in state.get("failed_tests", []):
            user_parts.append(f"- {ft['test_name']}: {ft['error_message']}")
            if ft.get("traceback"):
                user_parts.append(f"  Traceback:\n```\n{ft['traceback']}\n```")
        user_parts.append("")

        affected = state.get("affected_interfaces", [])
        user_parts.append("## 相关场景数据\n")
        for iface in state.get("scenarios", {}).get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            user_parts.append(f"### {iface['func']}")
            user_parts.append("```json")
            user_parts.append(json.dumps(iface.get("test_scenarios", []), ensure_ascii=False, indent=2))
            user_parts.append("```")
            user_parts.append("")

        client = AIClient()
        try:
            result = client.call(
                system_prompt=TEMPLATE_FIX_PROMPT,
                user_message="\n".join(user_parts),
                tool=FIX_PROPOSAL_TOOL,
            )
        except Exception as e:
            logger.error("AI template 修复失败: %s", e)
            return {
                "fix_action": "escalate_human",
                "fix_details": [],
                "fix_proposal_confidence": 0.0,
            }

        return {
            "fix_action": result.get("fix_action", "escalate_human"),
            "fix_details": result.get("fix_details", []),
            "fix_proposal_confidence": result.get("confidence", 0.4),
        }
