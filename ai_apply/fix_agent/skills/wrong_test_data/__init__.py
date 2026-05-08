"""
确定性修复 wrong_test_data 错误

根据语义约束（valid_range、enum_values、boundary_values）重新计算参数值。
复用 TestDataBuilder._build_args()，不调用 AI。
"""

import logging
import sys
import os

from ..base import BaseFixSkill

# 确保 ai_apply 在 path 上
_AI_APPLY_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")
if _AI_APPLY_DIR not in sys.path:
    sys.path.insert(0, os.path.normpath(_AI_APPLY_DIR))

logger = logging.getLogger("fix_agent.skills")


class WrongTestDataSkill(BaseFixSkill):
    category = "wrong_test_data"
    name = "wrong_test_data_fixer"

    @property
    def is_deterministic(self) -> bool:
        return True

    def execute(self, state: dict) -> dict:
        from data_builder import TestDataBuilder

        semantics = state.get("semantics", {})
        builder = TestDataBuilder(semantics)

        fix_details = []
        for iface, scenario, constraints in self._extract_affected_scenarios(state):
            old_args = scenario.get("args", [])
            new_args = builder._build_args(
                scenario.get("category", "normal"), constraints, scenario
            )

            if old_args != new_args:
                fix_details.append(self._build_fix_detail(
                    interface_func=iface["func"],
                    scenario_name=scenario["name"],
                    field_to_change="args",
                    proposed_value=new_args,
                    current_value=old_args,
                    reasoning=(
                        f"参数值不符合语义约束，根据 category={scenario.get('category')} "
                        f"和参数约束重新计算"
                    ),
                ))

        if not fix_details:
            return {
                "fix_action": "escalate_human",
                "fix_details": [],
                "fix_proposal_confidence": 0.0,
            }

        return {
            "fix_action": "modify_args",
            "fix_details": fix_details,
            "fix_proposal_confidence": 1.0,
        }
