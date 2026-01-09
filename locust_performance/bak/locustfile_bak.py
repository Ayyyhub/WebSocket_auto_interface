from locust import User, task, between


class RobotTeachingUser(User):
    """
    压测用户类 - 延迟导入项目代码，避免 Locust 在加载 locustfile 时卡死
    """
    wait_time = between(1, 3)

    def on_start(self):
        """用户启动时：建立连接并初始化"""
        # 这里再导入项目里的模块，避免在 locustfile 顶部就触发复杂逻辑
        from Connection.websocket_client import WSClient
        from Service.init_chain import ws_init_chain
        from core.ws_request import ws_clear_pending
        from utils.token_util import load_config, get_token
        from utils.logger import logger

        self._WSClient = WSClient
        self._ws_init_chain = ws_init_chain
        self._ws_clear_pending = ws_clear_pending
        self._load_config = load_config
        self._get_token = get_token
        self._logger = logger

        try:
            config = self._load_config()
            token, user_id = self._get_token()
            ws_url = config["ws_url"]

            self.ws_client = self._WSClient(ws_url, user_id, token)
            self.ws_client.connect()
            self._ws_clear_pending(self.ws_client)

            self._ws_init_chain(self.ws_client)
            self._logger.info(f"[Locust] User {user_id} 初始化完成")
        except Exception as e:
            self._logger.error(f"[Locust] User初始化失败: {e}")
            raise

    def on_stop(self):
        """用户停止时：关闭连接"""
        from utils.logger import logger

        if hasattr(self, "ws_client") and self.ws_client.connected:
            self.ws_client.close()
            logger.info("[Locust] WebSocket连接已关闭")

    @task(3)
    def load_model_flow(self):
        """任务1：加载模型流程（权重3）"""
        from Service.loadmodel_chain import LoadModel
        from utils.logger import logger

        try:
            load_model = LoadModel(ws_client=self.ws_client)
            load_model.ws_loadmodel_chain()
        except Exception as e:
            logger.error(f"[Locust] load_model_flow 失败: {e}")

    @task(1)
    def full_teaching_flow(self):
        """任务2：完整示教流程（权重1）"""
        from Service.amStart_chain import ws_amStart_chain
        from Service.teaching_chain import Teaching
        from utils.logger import logger

        try:
            started = ws_amStart_chain(self.ws_client)
            if not started:
                logger.error("[Locust] 控制器启动失败，跳过示教")
                return

            teaching = Teaching(self.ws_client)
            teaching.ws_teaching_chain()
        except Exception as e:
            logger.error(f"[Locust] full_teaching_flow 失败: {e}")