# 接口调用统一入口（send_request 升级）

from Adapter.switch_testmode import get_test_mode
from Adapter.ws_real import send_ws_real
from Adapter.ws_mock import send_ws_mock
from Adapter.ws_sandbox import send_ws_sandbox
from core.assertions import assert_resp_true
from core.ws_request import ws_send_and_wait
from tests.mock.mock_context import test_context
from utils.timestamp import get_unique_id
from utils.logger import logger

def send_request(ws_client, func, args, desc, owner=None):
    """
    owner: Teaching 实例（用于处理副作用）
    """
    # ===== 1️⃣ Pre-Invoke =====
    req_id = get_unique_id(func.split('.')[-1])
    req = {
        "func": func,
        "args": args,
        "id": req_id
    }

    # ===== 智能调度逻辑 =====

    # 1. 最高优先级：如果有显式的 Mock 数据 (@mock_response)，且针对当前接口，必须走 Mock
    if test_context.mock_overrides and func in test_context.mock_overrides:
        test_mode = "UNIT"

    # 2. 次高优先级：如果全局配置指定了 REAL/SANDBOX，优先遵从全局配置
    #    (允许在 @unittest_target 标记下进行真实接口测试)
    elif get_test_mode() in ["REAL", "SANDBOX"]:
        test_mode = get_test_mode()

    # 3. 低优先级：如果全局没配置，且标记了 Target，才默认回退到 UNIT
    elif test_context.current_target:
        test_mode = "UNIT"

    else:
        test_mode = get_test_mode()  # env 兜底

    # ===== 2️⃣ Invoke：选择 WS Adapter =====
    if test_mode == "UNIT":
        resp = send_ws_mock(req, desc)
    elif test_mode == "SANDBOX":
        resp = send_ws_sandbox(req, desc, ws_client)
    else:
        # 调用 send_ws_real 封装的 ws_request 的 ws_send_and_wait 方法
        # resp = send_ws_real(req, desc, ws_client)
        resp = ws_send_and_wait(
                req=req, 
                desc=desc, 
                ws_client=ws_client,
                continue_on_error=True # 发生错误不要直接抛死，返回 None 让 harness 处理
            )

    # ===== 3️⃣ Post-Invoke：统一断言 =====
    if resp:
        try:
            if not assert_resp_true(resp):
                logger.warning(f"{req_id} 断言失败！")
        except Exception as e:
            logger.warning(f"{req_id} 断言过程异常: {e}")

    return resp



