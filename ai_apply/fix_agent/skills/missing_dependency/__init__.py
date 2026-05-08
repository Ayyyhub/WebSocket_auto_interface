"""
混合修复 missing_dependency 错误

确定性部分：检查 semantics 中的 upstream.must_call_before，自动补前置步骤。
AI 回退：如果确定性部分无法解决，调用 AI 分析。
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

DEP_FIX_PROMPT = """\
你是一个自动化测试依赖分析专家。

当前测试失败的原因是缺少前置接口调用。请根据语义分析中的 upstream 依赖关系，
提出修复方案（通常是修改 args 以包含前置步骤所需的数据，或添加前置步骤）。

如果无法确定修复方案，选择 escalate_human。
"""


class MissingDependencySkill(BaseFixSkill):
    category = "missing_dependency"
    name = "missing_dependency_fixer"

    def execute(self, state: dict) -> dict:
        # 先尝试确定性修复
        result = self._try_deterministic(state)
        if result:
            return result

        # 确定性修不了，AI 兜底
        return self._ai_fallback(state)

    def _try_deterministic(self, state: dict) -> dict | None:
        """检查 upstream.must_call_before，确定性生成修复方案。"""
        semantics = state.get("semantics", {})
        affected = state.get("affected_interfaces", [])
        scenarios = state.get("scenarios", {})

        fix_details = []
        for iface_func in affected:
            for sem_iface in semantics.get("interfaces", []):
                if sem_iface["func"] != iface_func:
                    continue
                upstream = sem_iface.get("upstream", {})
                must_call = upstream.get("must_call_before", [])
                system_state = upstream.get("system_state", "")

                if must_call:
                    # 找到受影响接口中该函数的第一个场景
                    for iface in scenarios.get("interfaces", []):
                        if iface["func"] == iface_func:
                            for scenario in iface.get("test_scenarios", []):
                                # 只修 normal 场景的前置问题
                                if scenario.get("category") == "normal":
                                    fix_details.append(self._build_fix_detail(
                                        interface_func=iface_func,
                                        scenario_name=scenario["name"],
                                        field_to_change="description",
                                        proposed_value=(
                                            f"前置条件: 需先调用 {', '.join(must_call)}"
                                            + (f"；系统状态: {system_state}" if system_state else "")
                                        ),
                                        current_value=scenario.get("description", ""),
                                        reasoning=f"缺少前置调用: {', '.join(must_call)}",
                                    ))
                                    break
                            break

        if not fix_details:
            return None

        return {
            "fix_action": "add_setup_step",
            "fix_details": fix_details,
            "fix_proposal_confidence": 0.9,
        }

    def _ai_fallback(self, state: dict) -> dict:
        """AI 分析依赖问题并生成修复方案。"""
        from ai_client import AIClient
        from ..schemas import FIX_PROPOSAL_TOOL

        user_parts = []
        user_parts.append("## 错误分析\n")
        user_parts.append(f"根因: {state.get('root_cause', '')}")
        for ft in state.get("failed_tests", []):
            user_parts.append(f"- {ft['test_name']}: {ft['error_message']}")
        user_parts.append("")

        affected = state.get("affected_interfaces", [])
        user_parts.append("## 上游依赖信息\n")
        for iface in state.get("semantics", {}).get("interfaces", []):
            if affected and iface["func"] not in affected:
                continue
            upstream = iface.get("upstream", {})
            if upstream:
                user_parts.append(f"### {iface['func']}")
                user_parts.append(f"must_call_before: {upstream.get('must_call_before', [])}")
                user_parts.append(f"data_flow: {json.dumps(upstream.get('data_flow', []), ensure_ascii=False)}")
                user_parts.append("")

        user_parts.append("## 当前场景数据\n")
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
                system_prompt=DEP_FIX_PROMPT,
                user_message="\n".join(user_parts),
                tool=FIX_PROPOSAL_TOOL,
            )
        except Exception as e:
            logger.error("AI dependency 修复失败: %s", e)
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
