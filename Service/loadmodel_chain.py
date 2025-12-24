from core.harness import send_request
from Service.getalll4_chain import GetAll4
from utils.logger import logger

"""加载模型工作流"""

class LoadModel:
    loadObj_id = None


    def __init__(self,ws_client):
        self.ws_client = ws_client

    # 执行16-28号核心功能接口（加载模型）
    def ws_loadmodel_chain(self):
        try:
            # 16. 加载模型
            response_loadModel = send_request(self.ws_client, "sim.loadModel", ["public/models/robot/AIR4_560A/AIR4_560A.m"], "loadModel 加载模型")
            if response_loadModel and response_loadModel.get("success") and "ret" in response_loadModel and response_loadModel["ret"]:
                LoadModel.loadObj_id = response_loadModel["ret"][0]
                logger.info(f"[PERF] loadModel 加载模型成功，对象ID: {LoadModel.loadObj_id}")
            else:
                logger.warning(f"[PERF] loadModel 加载模型失败或返回空: {response_loadModel}")


            # 17. 获取对象位置
            send_request(self.ws_client, "sim.getObjectPosition", [LoadModel.loadObj_id, -1], "getObjectPosition 获取对象位置")

            # 18. 对象移动
            # args: 模型handle,[x,y,z]移动,参考对象handle"只有-1(world)和-11(parent)"，单位
            send_request(self.ws_client, "simArcs.webMoveObject", [LoadModel.loadObj_id, [0, 0, 0], -1, 4], "webMoveObject 对象移动")


            # 20. 获取handle类型
            send_request(self.ws_client, "simArcs.webGetHandleType", [LoadModel.loadObj_id], "webGetHandleType 获取加载模型的handle类型")


            # 21. 创建节点
            # args 控制器的工作台通道，节点类型
            response_ahmCreateHierarchyElement1 = send_request(self.ws_client, "simArcs.ahmCreateHierarchyElement", [0, 1], "ahmCreateHierarchyElement 创建节点")
            workbench_id = None
            if response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1.get("success") and "ret" in response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1["ret"]:
                workbench_id = response_ahmCreateHierarchyElement1["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建工作台节点成功，对象ID: {workbench_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建节点失败或返回空: {response_ahmCreateHierarchyElement1}")

            # 22. 设置父节点
            # args 节点ID，父节点ID
            send_request(self.ws_client, "simArcs.ahmSetElementParent", [workbench_id, 0], "ahmSetElementParent1 设置工作台父节点")

            # 23. 创建节点
            response_ahmCreateHierarchyElement2 = send_request(self.ws_client, "simArcs.ahmCreateHierarchyElement", [LoadModel.loadObj_id, 2], "ahmCreateHierarchyElement 创建节点")
            robot_id = None
            if response_ahmCreateHierarchyElement2 and response_ahmCreateHierarchyElement2.get("success") and "ret" in response_ahmCreateHierarchyElement2 and response_ahmCreateHierarchyElement2["ret"]:
                robot_id = response_ahmCreateHierarchyElement2["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建机器人的节点成功，对象ID: {robot_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建机器人的节点失败或返回空: {response_ahmCreateHierarchyElement2}")


            # 24. 设置父节点
            send_request(self.ws_client, "simArcs.ahmSetElementParent", [robot_id, workbench_id], "ahmSetElementParent 设置机器人的父节点")

            # # 24.1 获取节点名称
            # req_ahmGetElementName = {"func": "simArcs.ahmGetElementName", "args": [robot_id],"id": "ahmGetElementName"}
            # ws_send_and_wait(req_ahmGetElementName,"req_ahmGetElementName 获取节点名称")

            # 25. 获取场景树
            send_request(self.ws_client,"simArcs.ahmGetHierarchy",[],"ahmGetHierarchy 获取场景树")

            getall4= GetAll4(ws_client=self.ws_client)
            getall4.ws_getall4_chain()


        except Exception as e:
            logger.error(f"异常:{e}")

