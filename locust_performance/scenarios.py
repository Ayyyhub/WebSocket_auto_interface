# scenarios.py
from core.harness import send_request
from locust_performance.scenarios_stats import scenario_tracker


@scenario_tracker("load_model_flow")
def load_model_flow(user_instance):
    """
    任务函数：加载模型（权重 5）
    """
    from Service.loadmodel_chain import LoadModel
    from utils.logger import logger

    try:
        send_request(user_instance.ws_client, "wsRemoteApi.require", ["simArcs", "simAssimp", "simStepOrIges", "simIK"], "wsRemoteApi.require 加载后端simArcs的入口")
   
        load_model = LoadModel(ws_client=user_instance.ws_client)
        load_model.ws_loadmodel_chain()

    except Exception as e:
        # getattr(user_instance, 'user_id', 'unknown')：安全获取 user_instance（Locust 虚拟用户实例）的 user_id 属性 
        logger.error(
            f"[Locust][User {getattr(user_instance, 'user_id', 'unknown')}] "
            f"load_model_flow 失败: {e}"
        )
        raise  # 重新抛出异常，让装饰器记录为失败


@scenario_tracker("full_teaching_flow")
def full_teaching_flow(user_instance):
    """
    任务函数：完整示教流程（权重 1）
    """
    from Service.amStart_chain import ws_amStart_chain
    from Service.teaching_chain import Teaching
    from utils.logger import logger

    try:
        started = ws_amStart_chain(user_instance.ws_client)
        if not started:
            logger.error("[Locust] 控制器启动失败，跳过示教")
            return

        teaching = Teaching(user_instance.ws_client)
        teaching.ws_teaching_chain()
    except Exception as e:
        logger.error(f"[Locust] full_teaching_flow 失败: {e}")
        raise  # 重新抛出异常，让装饰器记录为失败


def load_model(user_instance):
    """
    任务函数：获取场景树（权重 3）
    """
    from utils.logger import logger
    from core.harness import send_request
    from locust_performance.assertions_locust import assert_response_locust, report_assertion_failure
    import time

    try:
        start_time = time.perf_counter()
        response = send_request(
            # user_instance.ws_client 就是这个 Locust 用户身上挂着的 WebSocket 客户端对象，在 BaseRobotUser.on_start() 里创建的。
            user_instance.ws_client, 
            "sim.loadModel", 
            ["public/models/robot/AIR4_560A/AIR4_560A.m"],
            "loadModel 加载模型"
        )
        elapsed_time = (time.perf_counter() - start_time) * 1000
        
        # 业务断言
        success, error_msg = assert_response_locust(
            response,
            "loadModel 加载模型",
            expect_success=True,
            expect_fields=["ret"]
        )
        
        if not success:
            report_assertion_failure("loadModel 加载模型", error_msg, elapsed_time)
            
    except Exception as e:
        logger.error(f"[Locust] load_model 失败: {e}")