"""
Fix Agent 条件边路由逻辑
"""

import logging

logger = logging.getLogger("fix_agent")


def route_after_skill(state: dict) -> str:
    """Skill 执行后路由：环境问题/无法修复 → END，低置信度 → 人工，否则 → 应用"""
    
    fix_action = state.get("fix_action", "")
    confidence = state.get("fix_proposal_confidence", 1.0)
    human_enabled = state.get("human_approval_enabled", True)
    error_category = state.get("error_category", "")

    # 环境问题直接终止
    if error_category == "environment_issue":
        logger.info("路由: 环境问题 → END")
        return "end"

    # 无法修复 + 人工审核关闭 → 终止
    if fix_action == "escalate_human" and not human_enabled:
        logger.info("路由: 无法修复且人工审核关闭 → END")
        return "end"

    # 无法修复 + 人工审核开启 → 人工介入
    if fix_action == "escalate_human" and human_enabled:
        logger.info("路由: 无法修复 → human_review")
        return "human_review"

    # 低置信度 + 人工审核开启 → 人工介入
    if confidence < 0.7 and human_enabled:
        logger.info("路由: 置信度 %.2f < 0.7 → human_review", confidence)
        return "human_review"

    # 正常路径：应用修复
    logger.info("路由: 置信度 %.2f → apply_fix", confidence)
    return "apply_fix"


def route_after_human(state: dict) -> str:
    """人工审核后路由"""
    
    decision = state.get("human_decision", "approve")

    if decision == "reject":
        logger.info("路由: 人工拒绝 → 重新分析")
        return "analyze_failure"

    logger.info("路由: 人工 %s → apply_fix", decision)
    return "apply_fix"


def route_after_retest(state: dict) -> str:
    """重测后路由：通过则结束，否则判断是否继续重试"""
    
    if state.get("all_passed", False):
        logger.info("路由: 全部通过 → END")
        return "end"

    retry_count = state.get("retry_count", 0)
    max_retries = state.get("max_retries", 3)

    if retry_count >= max_retries:
        logger.info("路由: 达到最大重试 %d 次 → END", max_retries)
        return "end"

    logger.info("路由: 第 %d 次重试 → parse_pytest_output", retry_count)
    return "parse_pytest_output"
