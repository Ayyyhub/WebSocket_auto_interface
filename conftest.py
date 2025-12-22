import pytest
import sys
import os
from Connection.websocket_client import WSClient
from utils.token_util import load_config, get_token,logout
from utils.logger import logger

# 确保项目根目录在 sys.path 中，防止导入模块报错
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

@pytest.fixture(scope="session")
def ws_client():
    """
    WebSocket 客户端 Fixture (Session 级别)
    作用：整个测试会话期间只建立一次连接，所有测试结束后自动关闭连接。
    """
    print() # 强制换行，避免日志紧接在 pytest 用例名称后面
    # 1. 加载配置
    try:
        config = load_config()
    except Exception as e:
        pytest.fail(f"加载配置文件失败: {e}")

    # 2. 获取Token (如果获取失败，token_util内部通常会抛出异常或断言失败)
    try:
        token, user_id = get_token()
    except Exception as e:
        pytest.fail(f"获取Token失败: {e}")
        
    # user_id 已从 get_token 获取
    ws_url = config.get("ws_url")
    
    if not ws_url:
        pytest.fail("配置文件中缺少 'ws_url'")
        
    logger.info(f"正在连接 WebSocket: {ws_url}")
    
    # 3. 初始化客户端
    client = WSClient(ws_url, user_id, token)
    
    # 4. 建立连接
    # WSClient.connect() 内部已实现了线程启动和连接等待逻辑
    try:
        client.connect()
    except Exception as e:
        logger.error(f"WebSocket 连接失败: {e}")
        pytest.fail(f"WebSocket 连接失败: {e}")
        
    # 5. 将客户端实例传递给测试用例
    yield client
    
    # 6. 测试结束后的清理工作 (Teardown)
    if client.connected:
        client.close()

    # 退出登录
    # if token:
    #     logout(token)
