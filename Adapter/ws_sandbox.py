from Adapter.ws_mock import send_ws_mock
from utils.logger import logger

def send_ws_sandbox(req, desc, ws_client=None):
    """
    Sandbox 适配器：目前暂未实现真实沙箱逻辑
    暂时复用 Mock 的行为，但在日志上做区分
    """
    logger.warning(f"[SANDBOX] (模拟沙箱环境) 处理请求: {desc}")
    
    # 这里未来可以对接一个本地启动的仿真器进程，或者一个特殊的 WS 端口
    # 目前先降级为 Mock
    return send_ws_mock(req, desc)