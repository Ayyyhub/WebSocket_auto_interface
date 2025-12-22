from core.ws_request import ws_send_and_wait
from utils.logger import logger
from utils.timestamp import get_unique_id


class NewPoint:
    def __init__(self, ws_client,generateObj_id,):
        self.ws_client = ws_client
        self.generateObj_id = generateObj_id


    """创建节点的四个接口"""
    def ws_newpoint_chain(self):
        try:
            # desc 获取handle类型
            req_webGetHandleType = {"func": "simArcs.webGetHandleType", "args": [self.generateObj_id], "id": get_unique_id('webGetHandleType')}
            resp_webGetHandleType=ws_send_and_wait(req_webGetHandleType, "webGetHandleType 获取handle类型", ws_client=self.ws_client)
            if resp_webGetHandleType and resp_webGetHandleType.get("success") and "ret" in resp_webGetHandleType and resp_webGetHandleType.get("ret"):
                handle_id = resp_webGetHandleType["ret"][0]
                logger.info(f"webGetHandleType 获取handle类型 成功，对象ID：{handle_id}")
            else:
                logger.warning(f"webGetHandleType 获取handle类型失败或返回空：{resp_webGetHandleType}")


            # desc 创建节点
            # args 机器人~模型传对应的handle,arl程序传对应的handle,采集点位路径 传对应的handle,目前只支持[0,5]
            # args 节点类型，0: 控制器，目前只支持1个\1: 工作台（通道），一个控制器最多支持6个\2: 机器人\3: 外部轴\4:  工具\5:  路径\6:  坐标系\7:  模型\8: arl程序\9: 采集点位路径\10: "模型"类型的子节点类型\11: 运动设备\12: 传送带
            req_ahmCreateHierarchyElement2 = {"func": "simArcs.ahmCreateHierarchyElement", "args": [self.generateObj_id, handle_id],
                                              "id": get_unique_id("ahmCreateHierarchyElement2")}
            r_ahmCreateHierarchyElement2 = ws_send_and_wait(req_ahmCreateHierarchyElement2,
                                                            "ahmCreateHierarchyElement 创建节点", ws_client=self.ws_client)
            generatePoint_id = None
            if r_ahmCreateHierarchyElement2 and r_ahmCreateHierarchyElement2.get(
                    "success") and "ret" in r_ahmCreateHierarchyElement2 and r_ahmCreateHierarchyElement2["ret"]:
                generatePoint_id = r_ahmCreateHierarchyElement2["ret"][0]
                logger.info(f"[PERF] ahmCreateHierarchyElement 创建节点成功，对象ID: {generatePoint_id}")
            else:
                logger.warning(f"[PERF] ahmCreateHierarchyElement 创建节点失败或返回空: {r_ahmCreateHierarchyElement2}")


            # desc 设置父节点
            req_ahmSetElementParent2 = {"func": "simArcs.ahmSetElementParent", "args": [generatePoint_id, -1],
                                        "id": get_unique_id("ahmSetElementParent2")}
            ws_send_and_wait(req_ahmSetElementParent2, "ahmSetElementParent 设置父节点", ws_client=self.ws_client)


            # desc 获取场景树
            req_ahmGetHierarchy2 = {"func": "simArcs.ahmGetHierarchy", "args": [], "id": get_unique_id("ahmGetHierarchy2")}
            ws_send_and_wait(req_ahmGetHierarchy2, "ahmGetHierarchy 获取场景树", ws_client=self.ws_client)

        except Exception as e:
            logger.error(e)