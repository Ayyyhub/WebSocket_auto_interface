from core.assertion import assert_resp_true
from core.ws_request import ws_send_and_wait
from utils.timestamp import get_unique_id
from utils.logger import logger

class GetAll4:
    def __init__(self, ws_client):
        self.ws_client = ws_client


    """获取配置信息的4个接口"""
    def ws_getall4_chain(self):

        #desc 获取所有坐标信息
        req_afmGetAll = {"func": "simArcs.afmGetAll", "id": get_unique_id("afmGetAll")}
        resp_afmGetAll=ws_send_and_wait(req_afmGetAll, "afmGetAll 获取所有坐标信息", ws_client=self.ws_client)
        if not assert_resp_true(resp_afmGetAll):
            logger.warning(f"{resp_afmGetAll['id']} 断言失败！")

        # desc 获取所有外部轴信息
        req_ejmGetAll = {"func": "simArcs.ejmGetAll", "args": [], "id": get_unique_id("ejmGetAll")}
        resp_ejmGetAll=ws_send_and_wait(req_ejmGetAll, "ejmGetAll 获取所有外部轴信息", ws_client=self.ws_client)
        if not assert_resp_true(resp_ejmGetAll):
            logger.warning(f"{resp_ejmGetAll['id']} 断言失败！")

        # desc 得到当前场景中信号的属性信息
        req_iomGetAllIOSignalActions = {"func": "simArcs.iomGetAllIOSignalActions", "id": get_unique_id("iomGetAllIOSignalActions")}
        resp_iomGetAllIOSignalActions=ws_send_and_wait(req_iomGetAllIOSignalActions, "iomGetAllIOSignalActions 得到当前场景中信号的属性信息",
                         ws_client=self.ws_client)
        if not assert_resp_true(resp_iomGetAllIOSignalActions):
            logger.warning(f"{req_iomGetAllIOSignalActions['id']} 断言失败！")

        # desc 获取机器人配置
        req_rmGetAll = {"func": "simArcs.rmGetAll", "args": [], "id": get_unique_id("rmGetAll")}
        resp_rmGetAll=ws_send_and_wait(req_rmGetAll, "rmGetAll_2 获取机器人配置", ws_client=self.ws_client)
        if not assert_resp_true(resp_rmGetAll):
            logger.warning(f"{req_rmGetAll['id']} 断言失败！")


