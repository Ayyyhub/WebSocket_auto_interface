# users.py
from locust import User, between
import time
from locust_performance.account_pool import account_pool
import requests
from utils.logger import logger

class BaseRobotUser(User):
    """
    所有压测用户的基类：
    - 负责：登录、建立 WebSocket 连接、初始化链路
    - 不负责：压哪些接口（交给 scenarios.py 里的任务）
    """
    
    abstract = True
    wait_time = between(1, 3)

    def on_start(self):
        """
        用户启动时：从账号池获取账号，登录，建立 WebSocket 连接
        """
        from Connection.websocket_client import WSClient
        from core.ws_request import ws_clear_pending
        from utils.conf_reader import load_config
        
        try:
            config = load_config()
            
            # 获取目标用户数（从 Locust 环境获取）
            target_user_count = None
            if hasattr(self.environment, 'runner') and self.environment.runner:
                target_user_count = getattr(self.environment.runner, 'target_user_count', None)
                logger.info(f"Locust 目标用户数: {target_user_count}")

            # 从账号池获取账号（按需加载）
            account = account_pool.get_account(target_user_count=target_user_count)
            if not account:
                raise Exception("无法从账号池获取账号")
            
            # 登录获取 token
            token, user_id = self._login(account, config)
            
            # 标记账号正在使用
            account_pool.mark_account_in_use(user_id, account)
            
            # 保存账号信息，用于退出时释放
            self.user_id = user_id
            self.account = account
            
            ws_url = config["ws_url"]
            
            # 初始化客户端
            self.ws_client = WSClient(ws_url, user_id, token)
            self.ws_client.connect()
            
            if self.ws_client.connected:
                print(f"User {user_id} 建立 WebSocket 链接成功！")
                ws_clear_pending(self.ws_client)
            else:
                print(f"User {user_id} 连接虽然没报错，但状态为未连接")

        except Exception as e:
            print(f"[Locust] User 初始化失败: {e}")
            time.sleep(1)
            raise e
    
    def _login(self, account, config):
        """
        使用账号登录获取 token
        :param account: 账号信息
        :param config: 配置信息
        :return: (token, user_id) 元组
        """
        name = account["name"]
        password = account["password"]
        checkCode = account["checkCode"]
        
        login_payload = {
            "name": name,
            "password": password,
            "checkCode": checkCode
        }
        
        response = requests.post(config['gte_token_url'], json=login_payload)
        response_data = response.json()
        
        if response_data.get('code') != 200 or response_data.get('data') is None:
            raise Exception(f"登录失败: {response_data}")
        
        token = response_data['data']['token']
        user_id = "pt" + str(response_data['data'].get('id'))
        
        return token, user_id

    def on_stop(self):
        """
        用户结束时：关闭连接，释放账号
        """
        from utils.logger import logger

        if hasattr(self, "ws_client") and self.ws_client.connected:
            self.ws_client.close()
            logger.info(f"[Locust] User {getattr(self, 'user_id', 'unknown')} WebSocket 连接已关闭")
        
        # 释放账号
        if hasattr(self, "user_id"):
            account_pool.release_account(self.user_id)


    