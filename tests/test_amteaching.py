import pytest
import allure
from Service.amStart_chain import ws_amStart_chain
from Service.init_chain import ws_init_chain
from Service.loadmodel_chain import LoadModel
from Service.teaching_chain import Teaching
from utils.logger import logger

@allure.feature("Create Program By Teaching")
class TestAmTeaching:

    @allure.story("Complete Teaching Process")
    @allure.title("执行完整的示教流程：初始化 -> 加载模型 -> 启动控制 -> 示教")
    def test_full_teaching_workflow(self, ws_client):
        """
        完整流程测试：
        1. 系统初始化
        2. 加载模型
        3. 启动控制器
        4. 执行示教动作并生成ARL程序
        """
        
        with allure.step("1. 系统初始化 (Init Chain)"):
            logger.info("Step 1: Initialization")
            ws_init_chain(ws_client)

        with allure.step("2. 加载模型 (Load Model)"):
            logger.info("Step 2: Load Model")
            load_model_instance = LoadModel(ws_client=ws_client)
            load_model_instance.ws_loadmodel_chain()
            # 可以在这里添加断言，例如检查 load_model_instance.loadObj_id 是否存在
            # assert load_model_instance.loadObj_id is not None, "Model load failed, ID is None"

        with allure.step("3. 开启使能 (Start Controller)"):
            logger.info("Step 3: Start Control")
            started = ws_amStart_chain(ws_client)
            assert started is True, "控制器启动失败 (Controller failed to start)"

        with allure.step("4. 执行示教 (Teaching)"):
            if started:
                logger.info("Step 4: Teaching")
                teaching_instance = Teaching(ws_client)
                teaching_instance.ws_teaching_chain()
                # 验证 ARL 程序 ID 是否生成
                with allure.step("验证 ARL 程序生成结果"):
                    assert Teaching.arl_id is not None, "示教流程结束，但未生成 ARL 程序 ID"
                    logger.info(f"验证通过: ARL ID = {Teaching.arl_id}")
            else:
                pytest.fail("由于控制器启动失败，跳过示教步骤")