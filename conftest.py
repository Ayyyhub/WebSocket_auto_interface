import time

import pytest
import sys
import os
from Connection.websocket_client import WSClient
from core.ws_request import ws_clear_pending
from utils.token_util import load_config, get_token,logout
from utils.logger import logger

# 注册 unit_fixtures 插件
pytest_plugins = [
    "tests.unit_fixtures.amStartJog_context",
]

# 确保项目根目录在 sys.path 中，防止导入模块报错
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Session 级别的 fixture 只有在 所有测试用例都跑完 之后才会执行 teardown
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
        time.sleep(5)
        client.close()
        time.sleep(3)
        logger.info("主动断连后，再次Websocket connected！")
        client.connect()
    except Exception as e:
        logger.error(f"WebSocket 连接失败: {e}")
        pytest.fail(f"WebSocket 连接失败: {e}")

    # 连接建立后，清理消息层缓存
    ws_clear_pending(client)
        
    # 5. 将客户端实例传递给测试用例
    yield client
    
    # 6. 测试结束后的清理工作 (Teardown)
    if client.connected:
        client.close()

    # 7. 退出登录
    # if token:
    #     logout(token)
