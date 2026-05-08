"""
Fix Agent CLI 入口

用法:
  python -m fix_agent.runner --dir loadmodel_chain --execute
  python -m fix_agent.runner --dir loadmodel_chain --resume loadmodel_chain
  python -m fix_agent.runner --dir loadmodel_chain --execute --no-human
  python -m fix_agent.runner --dir loadmodel_chain --execute --max-retries 5
"""

import argparse
import json
import logging
import os
import subprocess
import sys

# 将 ai_apply 目录加入 path
_AI_APPLY_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _AI_APPLY_DIR not in sys.path:
    sys.path.insert(0, _AI_APPLY_DIR)

from fix_agent.graph import build_fix_graph

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fix_agent.runner")


def run_pytest(test_file: str) -> str:
    """执行 pytest 并返回输出"""
    result = subprocess.run(
        ["pytest", test_file, "-v", "--tb=short"],
        capture_output=True, text=True, timeout=120,
    )
    return result.stdout + "\n" + result.stderr


def print_fix_proposal(state: dict):
    """在终端打印修复提案"""
    print("\n" + "=" * 60)
    print("AI 修复提案")
    print("=" * 60)
    print(f"错误分类: {state.get('error_category', '?')}")
    print(f"根因: {state.get('root_cause', '?')}")
    print(f"修复动作: {state.get('fix_action', '?')}")
    print(f"置信度: {state.get('fix_proposal_confidence', 0):.2f}")
    print()

    for detail in state.get("fix_details", []):
        print(f"  接口: {detail.get('interface_func', '?')}")
        print(f"  场景: {detail.get('scenario_name', '?')}")
        print(f"  修改: {detail.get('field_to_change', '?')}")
        print(f"  当前值: {detail.get('current_value', '?')}")
        print(f"  建议值: {detail.get('proposed_value', '?')}")
        if detail.get("reasoning"):
            print(f"  理由: {detail['reasoning']}")
        print()


def prompt_human_decision(state: dict) -> dict:
    """在终端交互获取人工审核结果"""
    print_fix_proposal(state)
    print("请选择操作:")
    print("  [y] 批准修复")
    print("  [n] 拒绝，让 AI 重新分析")
    print("  [m] 手动修改修复方案")

    while True:
        choice = input("\n> ").strip().lower()
        if choice in ("y", "yes", "approve"):
            return {"human_decision": "approve"}
        elif choice in ("n", "no", "reject"):
            return {"human_decision": "reject"}
        elif choice in ("m", "modify"):
            print("请输入修改后的 fix_details JSON（或输入 cancel 取消）:")
            json_str = input("> ").strip()
            if json_str.lower() == "cancel":
                continue
            try:
                modification = json.loads(json_str)
                return {
                    "human_decision": "modify",
                    "human_modification": modification,
                }
            except json.JSONDecodeError as e:
                print(f"JSON 解析失败: {e}，请重试")
        else:
            print("无效输入，请输入 y/n/m")


def main():
    parser = argparse.ArgumentParser(description="LangGraph Test Fix Agent")
    parser.add_argument("--dir", required=True,
                        help="ai_generated_testcases 下的目录名")
    parser.add_argument("--execute", action="store_true",
                        help="先执行 pytest 获取失败输出")
    parser.add_argument("--resume", type=str, default=None,
                        help="从断点恢复的 thread_id")
    parser.add_argument("--no-human", action="store_true",
                        help="关闭人工审核")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="最大重试次数（默认 3）")
    parser.add_argument("--sqlite", action="store_true",
                        help="使用 SQLite 持久化（支持崩溃恢复）")
    args = parser.parse_args()

    # 定位输出目录
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    output_dir = os.path.join(
        os.path.dirname(base_dir), "ai_generated_testcases", args.dir
    )
    if not os.path.isdir(output_dir):
        print(f"目录不存在: {output_dir}")
        sys.exit(1)

    # 执行 pytest 获取初始输出
    pytest_output = ""
    if args.execute:
        test_files = [f for f in os.listdir(output_dir)
                      if f.startswith("test_") and f.endswith(".py")]
        if test_files:
            print(f"执行 pytest: {test_files[0]}")
            pytest_output = run_pytest(os.path.join(output_dir, test_files[0]))
            print(pytest_output[:500])
        else:
            print(f"未找到测试文件: {output_dir}")
            sys.exit(1)

    # 构建 graph
    sqlite_path = os.path.join(output_dir, "fix_agent_checkpoint.db") if args.sqlite else None
    app = build_fix_graph(use_sqlite=args.sqlite, sqlite_path=sqlite_path)
    thread_id = args.resume or args.dir
    config = {"configurable": {"thread_id": thread_id}}

    # 构建初始状态（resume 时不传初始状态）
    if args.resume:
        print(f"从断点恢复: thread_id={thread_id}")
        initial_state = None
    else:
        initial_state = {
            "test_output_dir": output_dir,
            "scenario_name": args.dir,
            "pytest_output": pytest_output,
            "max_retries": args.max_retries,
            "human_approval_enabled": not args.no_human,
        }

    # 运行 graph（处理 interrupt）
    human_enabled = not args.no_human

    while True:
        try:
            result = app.invoke(initial_state, config=config)
            break
        except Exception as e:
            if "interrupt" in str(type(e).__name__).lower() or _is_interrupted(app, config):
                # Graph 被 interrupt 暂停（human_review 节点前）
                if not human_enabled:
                    # 不应该到这里，但安全起见直接继续
                    app.invoke(None, config=config)
                    continue

                # 获取当前状态
                state_snapshot = app.get_state(config)
                current_state = state_snapshot.values

                # 终端交互
                human_input = prompt_human_decision(current_state)

                # 将人工决策写入状态并恢复执行
                app.update_state(config, human_input, as_node="human_review")
                initial_state = None  # 后续继续不需要初始状态
            else:
                raise

    # 输出汇总
    _print_summary(result)


def _is_interrupted(app, config) -> bool:
    """检查 graph 是否在 interrupt 处暂停"""
    try:
        state = app.get_state(config)
        return state.next is not None and len(state.next) > 0
    except Exception:
        return False


def _print_summary(state: dict):
    """输出修复结果汇总"""
    print("\n" + "=" * 60)
    print("Fix Agent 完成")
    print("=" * 60)
    print(f"重试次数: {state.get('retry_count', 0)}")
    print(f"最终结果: {'全部通过' if state.get('all_passed') else '仍有失败'}")

    history = state.get("history", [])
    if history:
        print("\n修复历史:")
        for h in history:
            print(f"  第 {h.get('retry', '?')} 次: "
                  f"分类={h.get('category', '?')}, "
                  f"动作={h.get('action', '?')}, "
                  f"结果={h.get('result', '?')}")


if __name__ == "__main__":
    main()
