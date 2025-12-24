from core.harness import send_request

class GetAll4:
    def __init__(self, ws_client):
        self.ws_client = ws_client


    """获取配置信息的4个接口"""
    def ws_getall4_chain(self):

        #desc 获取所有坐标信息
        send_request(self.ws_client, "simArcs.afmGetAll", [], "afmGetAll 获取所有坐标信息")

        # desc 获取所有外部轴信息
        send_request(self.ws_client, "simArcs.ejmGetAll", [], "ejmGetAll 获取所有外部轴信息")

        # desc 获取当前场景中信号的属性信息
        send_request(self.ws_client, "simArcs.iomGetAllIOSignalActions", [], "iomGetAllIOSignalActions 得到当前场景中信号的属性信息")

        # desc 获取机器人配置
        send_request(self.ws_client, "simArcs.rmGetAll", [], "rmGetAll_2 获取机器人配置")


