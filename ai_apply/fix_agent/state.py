"""
Fix Agent 状态定义
"""

from enum import Enum
from typing import TypedDict, Optional


class ErrorCategory(str, Enum):
    WRONG_TEST_DATA = "wrong_test_data"
    WRONG_SCENARIO_LOGIC = "wrong_scenario_logic"
    MISSING_DEPENDENCY = "missing_dependency"
    ENVIRONMENT_ISSUE = "environment_issue"
    TEMPLATE_ISSUE = "template_issue"
    UNCERTAIN = "uncertain"


class FixAction(str, Enum):
    MODIFY_ARGS = "modify_args"
    MODIFY_EXPECTED = "modify_expected"
    REMOVE_SCENARIO = "remove_scenario"
    ADD_SETUP_STEP = "add_setup_step"
    MODIFY_ASSERTION = "modify_assertion"
    ESCALATE_HUMAN = "escalate_human"


class FixState(TypedDict, total=False):
    # --- 输入 ---
    test_output_dir: str               # 加载 ai_generated_testcases 下的 scenarios.json / semantics.json / workflow.json
    scenario_name: str                 # 场景名，如 loadmodel_chain
    pytest_output: str                 # pytest 原始输出
    max_retries: int                   # 默认 3
    human_approval_enabled: bool       # 默认 True

    # --- 已加载产物 ---
    scenarios: dict                    # scenarios.json
    semantics: dict                    # semantics.json
    workflow: dict                     # workflow.json（可选）

    # --- 分析 ---
    retry_count: int                   # 从 0 开始
    failed_tests: list[dict]           # [{test_name, error_message, traceback}]
    error_category: str                # ErrorCategory value
    root_cause: str                    # 人类可读的根因分析
    affected_interfaces: list[str]     # 受影响的接口函数名

    # --- 修复方案 ---
    fix_action: str                    # FixAction value
    fix_details: list[dict]            # 具体修改项
    fix_proposal_confidence: float     # 0.0-1.0

    # --- 执行 ---
    retest_output: str                 # 修复后的 pytest 输出
    all_passed: bool                   # 最终判定

    # --- 人工介入 ---
    human_decision: Optional[str]      # approve / reject / modify
    human_modification: Optional[dict] # 人工覆盖的 fix_details

    # --- 审计 ---
    history: list[dict]                # [{retry, category, action, result, snippet}]
