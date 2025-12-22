import time
from core.ws_request import ws_send_and_wait
from utils.logger import logger
from utils.timestamp import get_unique_id

"""开启使能"""
def ws_amStart_chain(ws_client):
    try:
        """开启使能"""
        # desc 开启使能
        req_amStart = {"func":"simArcs.amStart", "args": [0], "id": f"amStart_{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amStart, "amStart 开启使能",ws_client=ws_client)
        time.sleep(3)

        # desc 获取所有控制器
        req_amGetAll = {"func":"simArcs.amGetAll", "args": [], "id": f"amGetAll{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetAll,"amGetAll 获取所有控制器",ws_client=ws_client)

        # desc 获取可视化仿真状态
        req_amGetVisualSimulationState = {"func":"simArcs.amGetVisualSimulationState", "args": [], "id": f"amGetVisualSimulationState{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetVisualSimulationState,"amGetVisualSimulationState 获取可视化仿真状态",ws_client=ws_client)

        # desc 获取控制模式
        # args 机器人控制器索引
        req_amGetControlMode={"func":"simArcs.amGetControlMode", "args": [0], "id": f"amGetControlMode{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetControlMode,"amGetControlMode 获取控制模式",ws_client=ws_client)

        # desc 获取使能状态（手动、自动都用同一个接口）
        # args 机器人控制器索引
        req_amGetPowerState={"func":"simArcs.amGetPowerState", "args": [0], "id": f"amGetPowerState{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetPowerState,"amGetPowerState 获取使能状态",ws_client=ws_client)

        # desc 使能上电（手动模式）
        # args 机器人控制器索引，是否开启使能
        req_amSetEnableButtonState = {"func": "simArcs.amSetEnableButtonState", "args": [0, True],
                                      "id": f"amSetEnableButtonState{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amSetEnableButtonState, "req_amSetEnableButtonState 使能上电", ws_client=ws_client)
        time.sleep(3)


        """打开示教器"""
        # desc 切换通道（使能情况下）
        # args 机器人控制器索引，机器人通道ID
        req_amSwitchChannel={"func":"simArcs.amSwitchChannel", "args": [0,0], "id": f"amSwitchChannel{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amSwitchChannel,"amSwitchChannel 切换通道（使能情况下）",ws_client=ws_client)

        # desc 得到当前场景中信号的属性信息
        # req_iomGetAllIOSignalActions={"func":"simArcs.iomGetAllIOSignalActions", "args": [], "id": "iomGetAllIOSignalActions"}
        # ws_send_and_wait(req_iomGetAllIOSignalActions,"iomGetAllIOSignalActions 得到当前场景中信号的属性信息",ws_client=ws_client)

        # 关闭示教器界面停止推流
        req_aamStopPushMessageForTeachingPath={"func":"simArcs.aamStopPushMessageForTeachingPath", "args": [], "id": f"aamStopPushMessageForTeachingPath{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_aamStopPushMessageForTeachingPath,"simArcs.aamStopPushMessageForTeachingPath 关闭示教器界面停止推流",ws_client=ws_client)

        # desc 设置工件坐标系和机器人base之间的pose,[x y z ox oy oz ow]
        # args 机器人控制器索引，机器人通道ID，路径名称，世界坐标系'-1'
        req_aamSetWobjToBaseTr={"func":"simArcs.aamSetWobjToBaseTr","args": [0,0,'collect_point_path',-1], "id": f"aamSetWobjToBaseTr{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_aamSetWobjToBaseTr,"aamSetWobjToBaseTr 设置工件坐标系和机器人base之间的pose",ws_client=ws_client)

        # desc 打开示教器界面开始推流
        # args 机器人控制器索引，机器人通道ID，路径（“在没有生成示教点集的时候传入临时字符串，在生成示教点集合的时候传入 示教点集合的handle的字符串类型”）
        req_aamStartPushMessageForTeachingPath={"func":"simArcs.aamStartPushMessageForTeachingPath","args": [0,0,'collect_point_path'], "id": f"aamStartPushMessageForTeachingPath{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_aamStartPushMessageForTeachingPath,"aamStartPushMessageForTeachingPath 打开示教器界面开始推流",ws_client=ws_client)

        # desc 获取移动速率
        # args 机器人控制器索引，机器人通道ID
        req_amGetManuSpeed={"func":"simArcs.amGetManuSpeed","args": [0,0], "id": f"amGetManuSpeed{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetManuSpeed,"amGetManuSpeed 获取移动速率",ws_client=ws_client)

        # desc 获取轴模式
        # args 机器人控制器索引
        req_amGetManuAxisMode={"func":"simArcs.amGetManuAxisMode","args": [0], "id": f"amGetManuAxisMode{int(time.time() * 1000000)}"}
        ws_send_and_wait(req_amGetManuAxisMode,"amGetManuAxisMode 获取轴模式",ws_client=ws_client)

        # desc 打开示教器时删除机器人对应路径下采集点位的所有数据
        # args 机器人控制器索引，机器人通道ID，路径名称（“在没有生成示教点集的时候传入临时字符串，在生成示教点集合的时候传入示教点集合的handle的字符串类型”）
        req_aamClearLastRobotAndExJointStatusRecords={"func":"simArcs.aamClearLastRobotAndExJointStatusRecords","args":[0,0,'collect_point_path'],"id": get_unique_id("aamClearLastRobotAndExJointStatusRecords")}
        ws_send_and_wait(req_aamClearLastRobotAndExJointStatusRecords,"aamClearLastRobotAndExJointStatusRecords 打开示教器时删除机器人对应路径下采集点位的所有数据",ws_client=ws_client)

        return True

    except Exception as e:
        logger.error(e)
        return False