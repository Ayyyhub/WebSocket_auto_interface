from core.request_invoker import send_request
from Service.getalll4_chain import GetAll4
from utils.logger import logger

"""加载模型工作流"""

class LoadModel:
    object_handle = None
    loadObj_type = None
    obj_id = None
    robot_point_id = None

    def __init__(self,ws_client):
        self.ws_client = ws_client

    # 执行16-28号核心功能接口（加载模型）
    def ws_loadmodel_chain(self):
        try:
            # 16. 加载模型
            response_loadModel = send_request(self.ws_client, "sim.loadModel", ["public/models/robot/AIR4_560A/AIR4_560A.m"], "loadModel 加载模型")
            if response_loadModel and response_loadModel.get("success") and "ret" in response_loadModel and response_loadModel["ret"]:
                LoadModel.object_handle = response_loadModel["ret"][0]
                logger.info(f"[PERF] loadModel 加载模型成功，对象ID: {LoadModel.object_handle}")
            else:
                logger.warning(f"[PERF] loadModel 加载模型失败或返回空: {response_loadModel}")


            # 17. 获取对象位置
            send_request(self.ws_client, "sim.getObjectPosition", [LoadModel.object_handle, -1], "getObjectPosition 获取对象位置")

            # 18. 对象移动
            # args: 模型handle,[x,y,z]移动,参考对象handle"只有-1(world)和-11(parent)"，单位
            send_request(self.ws_client, "simArcs.webMoveObject", [LoadModel.object_handle, [0, 0, 0], -1, 4], "webMoveObject 对象移动")


            # 19. 获取加载的模型机器人的handle类型
            response_webGetHandleType=send_request(self.ws_client, "simArcs.webGetHandleType", [LoadModel.object_handle], "webGetHandleType 获取加载模型的handle类型")
            loadObj_type=None
            if response_webGetHandleType and response_webGetHandleType.get("success") and "ret" in response_webGetHandleType and response_webGetHandleType["ret"]:
                loadObj_type=response_webGetHandleType["ret"][0]
                logger.info(f"[PERF] webGetHandleType 获取加载的模型机器人的handle类型: {loadObj_type}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建节点失败或返回空: {response_webGetHandleType}")

            # 20. 创建节点
            # args 控制器的工作台通道，节点类型
            response_ahmCreateHierarchyElement1 = send_request(self.ws_client, "simArcs.ahmCreateHierarchyElement", [LoadModel.object_handle, 2], "ahmCreateHierarchyElement 创建工作台节点成功")
            obj_id = None
            if response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1.get("success") and "ret" in response_ahmCreateHierarchyElement1 and response_ahmCreateHierarchyElement1["ret"]:
                obj_id = response_ahmCreateHierarchyElement1["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建机器人，设置工作台节点成功，对象ID: {obj_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建节点失败或返回空: {response_ahmCreateHierarchyElement1}")

            # 21. 设置工作台父节点
            # args 节点ID，父节点ID
            send_request(self.ws_client, "simArcs.ahmSetElementParent", [obj_id, -1], "ahmSetElementParent1 设置工作台父节点")

            
            # 22. 获取节点名称
            req_ahmGetElementName = {"func": "simArcs.ahmGetElementName", "args": [obj_id],"id": "ahmGetElementName"}
            send_request(req_ahmGetElementName,"req_ahmGetElementName 获取节点名称")

            # 23. 获取场景树
            send_request(self.ws_client,"simArcs.ahmGetHierarchy",[],"ahmGetHierarchy 获取场景树")
            
            # getall4
            GetAll4(ws_client=self.ws_client).ws_getall4_chain()


        except Exception as e:
            logger.error(f"异常:{e}")

