from core.request_invoker import _ws_send_and_wait


def send_ws_real(req, desc, ws_client):
    """
    Real 适配器：调用真实的 WebSocket 发送逻辑
    """
    return _ws_send_and_wait(
        req=req,
        desc=desc,
        ws_client=ws_client,
        continue_on_error=True
    )
