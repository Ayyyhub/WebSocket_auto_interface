import json
from datetime import datetime
from utils.logger import logger


# ==================== 结果统计 ====================

_result_stats = []


def get_result_stats():
    """获取所有累积的请求结果统计"""
    return _result_stats


def clear_result_stats():
    """清空结果统计"""
    _result_stats.clear()


def record_result(desc, none_count, elapsed, success, fail_reason="", req_json=None, resp_json=None):
    """记录单次请求结果"""
    _result_stats.append({
        "desc": desc,
        "none_count": none_count,
        "elapsed": elapsed,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "success": success,
        "fail_reason": fail_reason,
        "req": req_json,
        "recv_req": resp_json,
    })


# ==================== 响应断言 ====================

def assert_resp_true(resp):
    """基础断言：校验响应结构是否合法"""
    if not isinstance(resp, dict):
        raise AssertionError(f"响应结果不是 dict: {type(resp)} {resp}")

    if "success" not in resp:
        raise AssertionError(f"响应结果缺少 success: {resp}")

    if resp["success"] != True:
        return False

    if "ret" not in resp:
        raise AssertionError(f"响应结果缺少 ret: {resp}")

    return True


def validate_response(resp, desc, expect_success=True, expect_ret=None,
                      continue_on_error=False, none_count=0, elapsed=0, req=None):
    """
    业务断言 + 统计记录。
    从原 ws_send_and_wait 中抽离的断言逻辑。
    返回 resp（通过或 continue），失败时根据 continue_on_error 决定抛异常还是返回。
    """
    req_json = json.dumps(req, ensure_ascii=False) if req else None
    resp_json = json.dumps(resp, ensure_ascii=False) if resp is not None else None

    # ret 为空数组 → 宽容通过
    if resp == [] or (isinstance(resp, dict) and resp.get("ret") == []):
        logger.info(f"{desc} 响应为空数组[]，已跳过断言")
        record_result(desc, none_count, elapsed, True, "响应为空数组，跳过断言", req_json, resp_json)
        return resp

    # expect_success 校验
    if expect_success and isinstance(resp, dict) and resp.get("success") is not True:
        fail_reason = f"success!=True, error: {resp.get('error', '')}"
        record_result(desc, none_count, elapsed, False, fail_reason, req_json, resp_json)
        if continue_on_error:
            logger.error(f"{desc} 失败: {resp}")
            return resp
        raise AssertionError(f"{desc} 失败: {resp}")

    # expect_ret 校验
    if expect_ret is not None and isinstance(resp, dict) and resp.get("ret") != expect_ret:
        fail_reason = f"ret不符, ret: {resp.get('ret', '')}"
        record_result(desc, none_count, elapsed, False, fail_reason, req_json, resp_json)
        if continue_on_error:
            logger.error(f"{desc} 返回ret不符: {resp}")
            return resp
        raise AssertionError(f"{desc} 返回ret不符: {resp}")

    # 正常通过
    logger.info(f"{desc} 接口响应成功，总耗时: {elapsed:.2f}s，None重试: {none_count}次")
    record_result(desc, none_count, elapsed, True, "", req_json, resp_json)
    return resp
