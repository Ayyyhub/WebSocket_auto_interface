"""
Fix Agent StateGraph 构建 + 编译
"""

import logging

from langgraph.graph import END, StateGraph

from .state import FixState
from .nodes import (
    load_artifacts,
    parse_pytest_output,
    analyze_failure,
    skill_dispatch,
    human_review,
    apply_fix,
    re_render,
    retest,
)
from .router import (
    route_after_skill,
    route_after_human,
    route_after_retest,
)

logger = logging.getLogger("fix_agent")


def build_fix_graph(use_sqlite: bool = False, sqlite_path: str = None):
    """
    构建 Fix Agent StateGraph。

    Args:
        use_sqlite: 是否使用 SQLite 持久化（崩溃恢复）
        sqlite_path: SQLite 数据库路径，默认 <output_dir>/fix_agent_checkpoint.db
    """

    graph = StateGraph(FixState)

    # ---- 添加节点 ----
    graph.add_node("load_artifacts", load_artifacts)
    graph.add_node("parse_pytest_output", parse_pytest_output)
    graph.add_node("analyze_failure", analyze_failure)
    graph.add_node("skill_dispatch", skill_dispatch)
    graph.add_node("human_review", human_review)
    graph.add_node("apply_fix", apply_fix)
    graph.add_node("re_render", re_render)
    graph.add_node("retest", retest)

    # ---- 入口 ----
    graph.set_entry_point("load_artifacts")

    # ---- 线性边 ----
    graph.add_edge("load_artifacts", "parse_pytest_output")
    graph.add_edge("parse_pytest_output", "analyze_failure")
    graph.add_edge("analyze_failure", "skill_dispatch")
    graph.add_edge("apply_fix", "re_render")
    graph.add_edge("re_render", "retest")

    # ---- 条件边 ----
    graph.add_conditional_edges("skill_dispatch", route_after_skill, {
        "apply_fix": "apply_fix",
        "human_review": "human_review",
        "end": END,
    })

    graph.add_conditional_edges("human_review", route_after_human, {
        "apply_fix": "apply_fix",
        "analyze_failure": "analyze_failure",
    })

    graph.add_conditional_edges("retest", route_after_retest, {
        "parse_pytest_output": "parse_pytest_output",
        "end": END,
    })

    # ---- 编译 ----
    if use_sqlite:
        try:
            from langgraph.checkpoint.sqlite import SqliteSaver
            checkpointer = SqliteSaver.from_conn_string(sqlite_path or "fix_agent_checkpoint.db")
            logger.info("使用 SQLite 持久化: %s", sqlite_path or "fix_agent_checkpoint.db")
        except ImportError:
            logger.warning("langgraph.checkpoint.sqlite 未安装，降级为 MemorySaver")
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
    else:
        from langgraph.checkpoint.memory import MemorySaver
        checkpointer = MemorySaver()

    # 当工作流马上要跑到 human_review 这个节点时，自动停下来，等待人工操作！
    return graph.compile(
        checkpointer=checkpointer,
        interrupt_before=["human_review"],  # 如果把这个关了就是自动模式，默认return "apply_fix"
    )
