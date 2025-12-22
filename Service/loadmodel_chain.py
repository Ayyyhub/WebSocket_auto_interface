from Service.getalll4_chain import GetAll4
from utils.logger import logger
from core.assertion import assert_resp_true
from core.ws_request import ws_send_and_wait
from utils.timestamp import get_unique_id

"""加载模型工作流"""

class LoadModel:
    loadObj_id = None


    def __init__(self,ws_client):
        self.ws_client = ws_client

    # 执行16-28号核心功能接口（加载模型）
    def ws_loadmodel_chain(self):
        try:
            # 16. 加载模型
            req_loadModel = {"func": "sim.loadModel", "args": ["public/models/robot/AIR4_560A/AIR4_560A.m"],
                             "id": get_unique_id("loadModel")}
            response_loadModel = ws_send_and_wait(req_loadModel, "loadModel 加载模型", ws_client=self.ws_client)
            if response_loadModel and response_loadModel.get("success") and "ret" in response_loadModel and response_loadModel["ret"]:
                LoadModel.loadObj_id = response_loadModel["ret"][0]
                logger.info(f"[PERF] loadModel 加载模型成功，对象ID: {LoadModel.loadObj_id}")
            else:
                logger.warning(f"[PERF] loadModel 加载模型失败或返回空: {response_loadModel}")
            if not assert_resp_true(response_loadModel):
                logger.warning(f"{req_loadModel['id']} 断言失败！")

            # 17. 获取对象位置
            req_getObjectPosition = {"func": "sim.getObjectPosition", "args": [LoadModel.loadObj_id, -1], "id": get_unique_id("getObjectPosition")}
            resp_getObjectPosition=ws_send_and_wait(req_getObjectPosition, "getObjectPosition 获取对象位置",ws_client=self.ws_client)
            if not assert_resp_true(resp_getObjectPosition):
                logger.warning(f"{req_getObjectPosition['id']} 断言失败！")

            # 18. 对象移动
            # args: 模型handle,[x,y,z]移动,参考对象handle"只有-1(world)和-11(parent)"，单位
            req_webMoveObject = {"func": "simArcs.webMoveObject",
                                 "args": [LoadModel.loadObj_id, [0, 0, 0], -1, 4],
                                 "id": get_unique_id("webMoveObject")}
            resp_webMoveObject=ws_send_and_wait(req_webMoveObject, "webMoveObject 对象移动",ws_client=self.ws_client)
            if not assert_resp_true(resp_webMoveObject):
                logger.warning(f"{req_webMoveObject['id']} 断言失败！")


            # 20. 获取handle类型
            req_webGetHandleType = {"func": "simArcs.webGetHandleType", "args": [LoadModel.loadObj_id], "id": get_unique_id("webGetHandleType")}
            resp_webGetHandleType=ws_send_and_wait(req_webGetHandleType, "webGetHandleType 获取加载模型的handle类型",ws_client=self.ws_client)
            if not assert_resp_true(resp_webGetHandleType):
                logger.warning(f"{req_webGetHandleType['id']} 断言失败!")


            # 21. 创建节点
            # args 控制器的工作台通道，节点类型
            req_ahmCreateHierarchyElement1 = {"func": "simArcs.ahmCreateHierarchyElement", "args": [0, 1],
                                              "id": get_unique_id("ahmCreateHierarchyElement1")}
            response_ahmCreateHierarchyElement1 = ws_send_and_wait(req_ahmCreateHierarchyElement1, "ahmCreateHierarchyElement 创建节点",ws_client=self.ws_client)
            workbench_id = None
            if response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1.get("success") and "ret" in response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1["ret"]:
                workbench_id = response_ahmCreateHierarchyElement1["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建工作台节点成功，对象ID: {workbench_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建节点失败或返回空: {response_ahmCreateHierarchyElement1}")
            if not assert_resp_true(response_ahmCreateHierarchyElement1):
                logger.warning(f"{req_ahmCreateHierarchyElement1['id']} 断言失败！")

            # 22. 设置父节点
            # args 节点ID，父节点ID
            req_ahmSetElementParent1 = {"func": "simArcs.ahmSetElementParent", "args": [workbench_id, 0],
                                        "id": get_unique_id("ahmSetElementParent1")}
            resp_ahmSetElementParent=ws_send_and_wait(req_ahmSetElementParent1, "ahmSetElementParent1 设置工作台父节点",ws_client=self.ws_client)
            if not assert_resp_true(resp_ahmSetElementParent):
                logger.warning(f"{req_ahmSetElementParent1['id']} 断言失败！")

            # 23. 创建节点
            req_ahmCreateHierarchyElement2 = {"func": "simArcs.ahmCreateHierarchyElement", "args": [LoadModel.loadObj_id, 2],
                                              "id": get_unique_id("ahmCreateHierarchyElement2")}
            response_ahmCreateHierarchyElement2 = ws_send_and_wait(req_ahmCreateHierarchyElement2, "ahmCreateHierarchyElement 创建节点",ws_client=self.ws_client)
            robot_id = None
            if response_ahmCreateHierarchyElement2 and response_ahmCreateHierarchyElement2.get("success") and "ret" in response_ahmCreateHierarchyElement2 and response_ahmCreateHierarchyElement2["ret"]:
                robot_id = response_ahmCreateHierarchyElement2["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建机器人的节点成功，对象ID: {robot_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建机器人的节点失败或返回空: {response_ahmCreateHierarchyElement2}")
            if not assert_resp_true(response_ahmCreateHierarchyElement2):
                logger.warning(f"{req_ahmCreateHierarchyElement2['id']} 断言失败！")


            # 24. 设置父节点
            req_ahmSetElementParent2 = {"func": "simArcs.ahmSetElementParent", "args": [robot_id, workbench_id],
                                        "id": get_unique_id("ahmSetElementParent2")}
            resp_ahmSetElementParent2=ws_send_and_wait(req_ahmSetElementParent2, "ahmSetElementParent 设置机器人的父节点",ws_client=self.ws_client)
            if not assert_resp_true(resp_ahmSetElementParent2):
                logger.warning(f"{req_ahmSetElementParent2['id']} 断言失败！")

            # # 24.1 获取节点名称
            # req_ahmGetElementName = {"func": "simArcs.ahmGetElementName", "args": [robot_id],"id": "ahmGetElementName"}
            # ws_send_and_wait(req_ahmGetElementName,"req_ahmGetElementName 获取节点名称")

            # 25. 获取场景树
            req_ahmGetHierarchy = {"func": "simArcs.ahmGetHierarchy", "args": [], "id": get_unique_id("ahmGetHierarchy")}
            resp_ahmGetHierarchy=ws_send_and_wait(req_ahmGetHierarchy, "ahmGetHierarchy 获取场景树",ws_client=self.ws_client)
            if not assert_resp_true(resp_ahmGetHierarchy):
                logger.warning(f"{resp_ahmGetHierarchy['id']} 断言失败！")

            getall4= GetAll4(ws_client=self.ws_client)
            getall4.ws_getall4_chain()


        except Exception as e:
            logger.error(f"异常:{e}")

