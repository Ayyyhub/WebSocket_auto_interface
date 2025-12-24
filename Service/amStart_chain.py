import time
from core.harness import send_request
from utils.logger import logger

"""开启使能"""
def ws_amStart_chain(ws_client):
    try:
        """启动控制器，开启使能"""
        # desc 启动控制器，开启使能
        send_request(ws_client, "simArcs.amStart", [0], "amStart 开启使能")
        time.sleep(3)

        # desc 获取所有控制器
        send_request(ws_client, "simArcs.amGetAll", [], "amGetAll 获取所有控制器")

        # desc 获取可视化仿真状态
        send_request(ws_client, "simArcs.amGetVisualSimulationState", [], "amGetVisualSimulationState 获取可视化仿真状态")

        # desc 获取控制模式
        # args 机器人控制器索引
        send_request(ws_client, "simArcs.amGetControlMode", [0], "amGetControlMode 获取控制模式")

        # desc 获取使能状态（手动、自动都用同一个接口）
        # args 机器人控制器索引
        send_request(ws_client, "simArcs.amGetPowerState", [0], "amGetPowerState 获取使能状态")

        # desc 使能下电（手动模式）
        send_request(ws_client, "simArcs.amSetEnableButtonState", [0, False], "req_amSetEnableButtonState 使能下电")

        # desc 使能上电（手动模式）
        # args 机器人控制器索引，是否开启使能
        send_request(ws_client, "simArcs.amSetEnableButtonState", [0, True], "req_amSetEnableButtonState 使能上电")
        time.sleep(3)


        """打开示教器"""
        # desc 切换通道（使能情况下）
        # args 机器人控制器索引，机器人通道ID
        send_request(ws_client, "simArcs.amSwitchChannel", [0, 0], "amSwitchChannel 切换通道（使能情况下）")

        # 关闭示教器界面停止推流
        send_request(ws_client, "simArcs.aamStopPushMessageForTeachingPath", [], "simArcs.aamStopPushMessageForTeachingPath 关闭示教器界面停止推流")

        # desc 设置工件坐标系和机器人base之间的pose,[x y z ox oy oz ow]
        # args 机器人控制器索引，机器人通道ID，路径名称，世界坐标系'-1'
        send_request(ws_client, "simArcs.aamSetWobjToBaseTr", [0, 0, 'collect_point_path', -1], "aamSetWobjToBaseTr 设置工件坐标系和机器人base之间的pose")

        # desc 打开示教器界面开始推流
        # args 机器人控制器索引，机器人通道ID，路径（“在没有生成示教点集的时候传入临时字符串，在生成示教点集合的时候传入 示教点集合的handle的字符串类型”）
        send_request(ws_client, "simArcs.aamStartPushMessageForTeachingPath", [0, 0, 'collect_point_path'], "aamStartPushMessageForTeachingPath 打开示教器界面开始推流")

        # desc 获取移动速率
        # args 机器人控制器索引，机器人通道ID
        send_request(ws_client, "simArcs.amGetManuSpeed", [0, 0], "amGetManuSpeed 获取移动速率")

        # desc 获取轴模式
        # args 机器人控制器索引
        send_request(ws_client, "simArcs.amGetManuAxisMode", [0], "amGetManuAxisMode 获取轴模式")

        return True

    except Exception as e:
        logger.error(e)
        return False