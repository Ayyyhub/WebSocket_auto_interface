"""
Fix Agent Tool Schema 定义
遵循 ai_client.py 中 WORKFLOW_TOOL / SEMANTICS_TOOL / SCENARIOS_TOOL 的模式
"""

ERROR_ANALYSIS_TOOL = {
    "type": "function",
    "function": {
        "name": "output_error_analysis",
        "description": "分析 pytest 测试失败结果，输出错误分类和根因分析",
        "parameters": {
            "type": "object",
            "properties": {
                "failed_tests": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "test_name": {"type": "string", "description": "失败的测试函数名"},
                            "interface_func": {"type": "string", "description": "对应的接口函数名"},
                            "error_summary": {"type": "string", "description": "错误摘要"},
                            "traceback_snippet": {"type": "string", "description": "关键 traceback 片段"},
                        },
                        "required": ["test_name", "error_summary"],
                    },
                },

                "error_category": {
                    "type": "string",
                    "enum": [
                        "wrong_test_data", "wrong_scenario_logic",
                        "missing_dependency", "environment_issue",
                        "template_issue", "uncertain",
                    ],
                    "description": (
                        "wrong_test_data: 测试参数值不合理（边界值错误、类型不匹配等）\n"
                        "wrong_scenario_logic: 测试场景的预期结果写反了（应成功却期望失败，或反之）\n"
                        "missing_dependency: 前置接口未调用，导致状态不满足\n"
                        "environment_issue: WebSocket 连接失败、认证过期等环境问题\n"
                        "template_issue: 渲染模板生成的代码有语法或逻辑问题\n"
                        "uncertain: 无法确定原因"
                    ),
                },

                "root_cause": {"type": "string", "description": "详细的根因分析（中文）"},
                
                "affected_interfaces": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "受影响的接口函数名列表",
                },
                
                "confidence": {
                    "type": "number",
                    "description": "分析置信度 0.0-1.0，低于 0.7 将触发人工审核",
                },
            },
            "required": ["failed_tests", "error_category", "root_cause"],
        },
    },
}

FIX_PROPOSAL_TOOL = {
    "type": "function",
    "function": {
        "name": "output_fix_proposal",
        "description": "根据错误分析结果，输出具体的修复方案（修改 scenarios.json 中的字段）",
        "parameters": {
            "type": "object",
            "properties": {
                "fix_action": {
                    "type": "string",
                    "enum": [
                        "modify_args", "modify_expected",
                        "remove_scenario", "add_setup_step",
                        "modify_assertion", "escalate_human",
                    ],
                    "description": (
                        "modify_args: 修改测试参数值\n"
                        "modify_expected: 修改预期结果（should_success 或 assertions）\n"
                        "remove_scenario: 删除不合理的测试场景\n"
                        "add_setup_step: 添加前置步骤\n"
                        "modify_assertion: 修改断言逻辑\n"
                        "escalate_human: 无法自动修复，需要人工介入"
                    ),
                },
                "confidence": {
                    "type": "number",
                    "description": "修复方案置信度 0.0-1.0",
                },
                "fix_details": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "interface_func": {
                                "type": "string",
                                "description": "接口函数名，如 sim.loadModel",
                            },
                            "scenario_name": {
                                "type": "string",
                                "description": "测试场景名，如 test_loadModel_normal",
                            },
                            "field_to_change": {
                                "type": "string",
                                "enum": [
                                    "args", "expected.should_success",
                                    "expected.assertions", "category",
                                    "description", "__remove__",
                                ],
                                "description": (
                                    "args: 替换参数列表\n"
                                    "expected.should_success: 修改预期是否成功\n"
                                    "expected.assertions: 替换断言列表\n"
                                    "category: 修改场景分类\n"
                                    "description: 修改场景描述\n"
                                    "__remove__: 删除整个场景"
                                ),
                            },
                            "current_value": {
                                "type": "string",
                                "description": "当前值的 JSON 字符串",
                            },
                            "proposed_value": {
                                "type": "string",
                                "description": "建议值的 JSON 字符串",
                            },
                            "reasoning": {
                                "type": "string",
                                "description": "为什么这样修改（中文）",
                            },
                        },
                        "required": [
                            "interface_func", "scenario_name",
                            "field_to_change", "proposed_value",
                        ],
                    },
                },
                "reasoning": {
                    "type": "string",
                    "description": "整体修复思路（中文）",
                },
            },
            "required": ["fix_action", "fix_details"],
        },
    },
}
