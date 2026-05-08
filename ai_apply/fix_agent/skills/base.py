"""
Fix Skill 基类

每个 skill 处理一种 ErrorCategory，返回与 propose_fix 相同格式的 state 更新。
"""

import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("fix_agent.skills")


class BaseFixSkill(ABC):
    """
    所有修复 skill 的抽象基类。

    子类必须设置:
        - category: ErrorCategory 值字符串
        - name: 日志用的人类可读名称

    子类必须实现:
        - execute(state: dict) -> dict
    """

    category: str = ""
    name: str = ""

    @property
    def is_deterministic(self) -> bool:
        """True 表示纯代码逻辑，不调用 AI。"""
        
        return False

    @abstractmethod
    def execute(self, state: dict) -> dict:
        """
        执行修复逻辑，返回 state 更新 dict。

        返回值必须包含:
            - fix_action: str
            - fix_details: list[dict]
            - fix_proposal_confidence: float
        """
        ...

    def _extract_affected_scenarios(self, state: dict) -> list[tuple]:
        """
        提取受影响接口的场景数据。

        Returns:
            [(interface_dict, scenario_dict, param_constraints), ...]
        """

        affected = state.get("affected_interfaces", [])
        scenarios = state.get("scenarios", {})
        semantics = state.get("semantics", {})

        param_map = {}
        for iface in semantics.get("interfaces", []):
            param_map[iface["func"]] = iface.get("params", [])

        results = []
        for iface in scenarios.get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            constraints = param_map.get(iface["func"], [])
            for scenario in iface.get("test_scenarios", []):
                results.append((iface, scenario, constraints))

        return results

    def _build_fix_detail(
        self,
        interface_func: str,
        scenario_name: str,
        field_to_change: str,
        proposed_value,
        reasoning: str,
        current_value=None,
    ) -> dict:
        """构造标准 fix_detail dict。"""

        detail = {
            "interface_func": interface_func,
            "scenario_name": scenario_name,
            "field_to_change": field_to_change,
            "proposed_value": (
                json.dumps(proposed_value, ensure_ascii=False)
                if not isinstance(proposed_value, str)
                else proposed_value
            ),
            "reasoning": reasoning,
        }
        if current_value is not None:
            detail["current_value"] = (
                json.dumps(current_value, ensure_ascii=False)
                if not isinstance(current_value, str)
                else current_value
            )
        return detail
