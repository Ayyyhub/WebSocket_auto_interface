from core.ws_request import ws_send_and_wait

def send_ws_real(req, desc, ws_client):
    """
    Real 适配器：调用真实的 WebSocket 发送逻辑
    """
    
    return ws_send_and_wait(
        req=req, 
        desc=desc, 
        ws_client=ws_client,
        continue_on_error=True # 发生错误不要直接抛死，返回 None 让 harness 处理
    )