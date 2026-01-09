# locust_performance/assertions_locust.py
from locust import events
from utils.logger import logger


def assert_response_locust(response, name, expect_success=True, expect_fields=None):
    """
    断言响应结果
    :param response: 响应数据
    :param name: 接口名称
    :param expect_success: 是否期望 success == True
    :param expect_fields: 期望存在的字段列表，如 ["ret", "data"]
    :return: (是否通过, 错误信息)
    """
    if response is None:
        return False, f"{name} 响应为空"
    
    # 检查 success 字段
    if expect_success:
        if not isinstance(response, dict):
            return False, f"{name} 响应格式错误：不是字典类型"
        if response.get("success") != True:
            error_msg = response.get("error", "未知错误")
            return False, f"{name} 业务失败：{error_msg}"
    
    # 检查必需字段
    if expect_fields:
        for field in expect_fields:
            if field not in response:
                return False, f"{name} 响应缺少必需字段：{field}"
    
    return True, None

def report_assertion_failure(name, error_msg, response_time=0):
    """
    上报断言失败到 Locust 统计
    """
    events.request.fire(
        request_type="ASSERTION",
        name=name,
        response_time=response_time,
        response_length=0,
        exception=Exception(error_msg)
    )
    logger.error(f"[断言失败] {name}: {error_msg}")