"""
确定性处理 environment_issue

环境问题无法通过修改 scenarios.json 解决，标记终止。
"""

import logging

from ..base import BaseFixSkill

logger = logging.getLogger("fix_agent.skills")


class EnvironmentIssueSkill(BaseFixSkill):
    category = "environment_issue"
    name = "environment_issue_handler"

    @property
    def is_deterministic(self) -> bool:
        return True

    def execute(self, state: dict) -> dict:
        root_cause = state.get("root_cause", "未知环境问题")
        logger.warning("环境问题，无法自动修复: %s", root_cause)

        return {
            "fix_action": "escalate_human",
            "fix_details": [],
            "fix_proposal_confidence": 0.0,
            "all_passed": False,
        }
