# locust_performance/monitors.py
from locust import events
from utils.logger import logger

# 响应时间阈值配置（单位：毫秒）
RESPONSE_TIME_THRESHOLDS = {
    "default": 5000,  # 默认阈值
    # 可以按接口名设置不同阈值
    "加载模型接口": 5000,
    "完整示教流程": 5000,
}

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception=None, **kwargs):
    """
    监听所有请求事件（包括 WebSocket 请求）
    因为你的代码中通过 events.request.fire() 手动上报了 WebSocket 请求
    所以这个监听器可以监听到所有请求
    """
    # 获取该接口的阈值（优先使用接口名，否则使用默认值）
    threshold = RESPONSE_TIME_THRESHOLDS.get(name, RESPONSE_TIME_THRESHOLDS["default"])
    
    # 响应时间超阈值告警
    if response_time > threshold:
        warning_msg = f"⚠️ 【响应超时告警】接口: {name}, 响应时间: {response_time}ms, 阈值: {threshold}ms"
        print(warning_msg)
        logger.warning(warning_msg)
    
    # 异常告警
    if exception:
        error_msg = f"❌ 【请求失败】接口: {name}, 异常: {exception}"
        print(error_msg)
        logger.error(error_msg)