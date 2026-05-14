"""
确定性修复 wrong_scenario_logic 错误

处理测试场景的预期结果写反的情况。
当服务端对异常参数做容错返回 success=True，但测试预期 success=False 时，
直接翻转 should_success 并调整 assertions。
"""

import json
import logging
import re
from ..base import BaseFixSkill

logger = logging.getLogger("fix_agent.skills")


def _fuzzy_match(scenario_name: str, test_name: str) -> bool:
    """
    模糊匹配场景名和测试函数名。
    场景名: test_webGetHandleType_wrong_arg_type
    测试名: test_step4_webGetHandleType_wrong_arg_type
    去掉 step\d+_ 后比较。
    """
    clean_test = re.sub(r"_step\d+", "", test_name)
    return scenario_name == clean_test or scenario_name in test_name


class WrongScenarioLogicSkill(BaseFixSkill):
    category = "wrong_scenario_logic"
    name = "wrong_scenario_logic_fixer"

    @property
    def is_deterministic(self) -> bool:
        return True

    def execute(self, state: dict) -> dict:
        failed_tests = state.get("failed_tests", [])
        failed_names = {ft["test_name"] for ft in failed_tests}

        # 如果 scenarios 中没有 should_success 字段，直接给 expected 里加上
        scenarios = state.get("scenarios", {})
        has_should_success = any(
            sc.get("expected", {}).get("should_success") is not None
            for iface in scenarios.get("interfaces", [])
            for sc in iface.get("test_scenarios", [])
        )

        fix_details = []
        for iface, scenario, _ in self._extract_affected_scenarios(state):
            scenario_name = scenario.get("name", "")

            # 匹配失败用例
            if not any(_fuzzy_match(scenario_name, fn) for fn in failed_names):
                continue

            expected = scenario.get("expected", {})
            should_success = expected.get("should_success")

            # should_success 为 None 或 False 时都需要修改
            if should_success is True:
                continue

            fix_details.append(self._build_fix_detail(
                interface_func=iface["func"],
                scenario_name=scenario_name,
                field_to_change="expected.should_success",
                proposed_value="true",
                current_value=str(should_success).lower() if should_success is not None else "null",
                reasoning=(
                    f"场景 {scenario_name} (category={scenario.get('category')}) "
                    f"预期 success=False，但服务端容错返回了 success=True。"
                    f"将 expected.should_success 改为 true。"
                ),
            ))

        if not fix_details:
            logger.warning("wrong_scenario_logic: 未找到需要修改的场景")
            return {
                "fix_action": "escalate_human",
                "fix_details": [],
                "fix_proposal_confidence": 0.0,
            }

        return {
            "fix_action": "modify_expected",
            "fix_details": fix_details,
            "fix_proposal_confidence": 0.95,
        }
