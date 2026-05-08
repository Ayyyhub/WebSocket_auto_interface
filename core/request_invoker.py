# 接口调用统一入口（send_request）
# 职责：请求构建 → 模式调度 → 发送等待 → 断言记录

import json
import time

from Adapter.mode.switch_testmode import get_test_mode
from Adapter.mode.ws_mock import send_ws_mock
from Adapter.mode.ws_sandbox import send_ws_sandbox
from Message.dispatcher import NonJsonMessageError, ResponseTimeoutError, get_dispatcher
from core.assertions import assert_resp_true, validate_response, record_result
from tests.mock.mock_context import test_context
from utils.timestamp import get_unique_id
from utils.logger import logger


# ==================== WebSocket 发送+等待 ====================

def _ws_send_and_wait(req, desc, expect_success=True, expect_ret=None,
                      max_none_retry=3, timeout_per_recv=5, ws_client=None,
                      continue_on_error=False):
    """发送 WebSocket 请求并等待响应"""
    dispatcher = get_dispatcher(ws_client)
    req_id = str(req.get("id"))
    ws_client.send(req)
    start_time = time.time()

    try:
        parsed_response, none_count, elapsed = dispatcher.wait_for_response(
            req_id, desc, max_none_retry=max_none_retry, timeout_per_recv=timeout_per_recv
        )
    except ResponseTimeoutError as e:
        logger.info(f"{desc}连续{max_none_retry}次无响应")
        record_result(desc, e.none_count, time.time() - start_time,
                      False, f"连续{max_none_retry}次无响应",
                      json.dumps(req, ensure_ascii=False), None)
        if continue_on_error:
            logger.error(f"{desc}连续{max_none_retry}次无响应 (已忽略错误)")
            return None
        raise AssertionError(f"{desc}连续{max_none_retry}次无响应")
    except NonJsonMessageError as e:
        logger.info(f"{desc}收到非json响应: {e.raw_message}")
        record_result(desc, 0, time.time() - start_time,
                      False, "非json响应",
                      json.dumps(req, ensure_ascii=False), e.raw_message)
        if continue_on_error:
            logger.error(f"{desc}收到非json响应 (已忽略错误)")
            return None
        raise AssertionError(f"{desc}收到非json响应")

    logger.info(f"请求体: {req}")
    logger.info(f"响应体: {parsed_response}")

    # 断言 + 统计记录（委托给 assertions 模块）
    result = validate_response(
        parsed_response, desc,
        expect_success=expect_success, expect_ret=expect_ret,
        continue_on_error=continue_on_error,
        none_count=none_count, elapsed=elapsed, req=req
    )
    time.sleep(0.3)
    return result


# ==================== 统一入口 ====================

def send_request(ws_client, func, args, desc, owner=None):
    """
    接口调用统一入口。
    owner: Service 实例（用于处理副作用，如 Teaching）
    """
    # Pre-Invoke：构建请求
    req_id = get_unique_id(func.split('.')[-1])
    req = {
        "func": func,
        "args": args,
        "id": req_id
    }

    # 智能调度逻辑
    if test_context.mock_overrides and func in test_context.mock_overrides:
        test_mode = "UNIT"
    elif get_test_mode() in ["REAL", "SANDBOX"]:
        test_mode = get_test_mode()
    elif test_context.current_target:
        test_mode = "UNIT"
    else:
        test_mode = get_test_mode()

    # Invoke：选择适配器
    if test_mode == "UNIT":
        resp = send_ws_mock(req, desc)
    elif test_mode == "SANDBOX":
        resp = send_ws_sandbox(req, desc, ws_client)
    else:
        resp = _ws_send_and_wait(
            req=req, desc=desc, ws_client=ws_client,
            continue_on_error=True
        )

    # Post-Invoke：统一断言
    if resp:
        try:
            if not assert_resp_true(resp):
                logger.warning(f"{req_id} 断言失败！")
        except Exception as e:
            logger.warning(f"{req_id} 断言过程异常: {e}")

    return resp
