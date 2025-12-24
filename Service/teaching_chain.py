from Service.getalll4_chain import GetAll4
from Service.loadmodel_chain import LoadModel
from Service.newpoint_chain import NewPoint
from utils.logger import logger
from core.harness import send_request

class Teaching:
    # 示教点集 ID
    collect_point_path_id=None
    # 程序 ID
    arl_id = None

    def __init__(self,ws_client):
        self.ws_client = ws_client

    """开始示教"""
    def ws_teaching_chain(self):
        loadmodel_instance = LoadModel(self.ws_client)
        # 初始化关键变量，避免后续引用报错

        try:
            # === 1. 运动控制流程（不需要返回值,需要启动控制器amStart） ===
            
            # 单轴模式下开始逆向转动1轴
            send_request(self.ws_client, "simArcs.amStartJog", [0, 1, 1], "amStartJog 转动轴", owner=self)
            # 停止转动
            send_request(self.ws_client, "simArcs.amStopJog", [0], "amStopJog 停止转动", owner=self)
            # 采集点位
            send_request(self.ws_client, "simArcs.aamCaptureCurrRobotAndExJointStatus", [0, 0, 0, 'collect_point_path'], "aamCaptureCurrRobotAndExJointStatus 采集点位", owner=self)
            # 切换笛卡尔模式
            send_request(self.ws_client, "simArcs.amSetManuAxisMode", [0, 1], "amSetManuAxisMode", owner=self)
            # 移动Z轴
            send_request(self.ws_client, "simArcs.amStartJog", [0, 3, 1], "amStartJog 笛卡尔模式下朝Z轴方向移动", owner=self)
            # 停止
            send_request(self.ws_client, "simArcs.amStopJog", [0], "amStopJog 停止转动", owner=self)
            # 绕Z轴旋转
            send_request(self.ws_client, "simArcs.amStartJog", [0, 4, 1], "amStartJog 绕Z轴旋转", owner=self)
            # 停止
            send_request(self.ws_client, "simArcs.amStopJog", [0], "amStopJog 停止旋转", owner=self)
            # 采集点位
            send_request(self.ws_client, "simArcs.aamCaptureCurrRobotAndExJointStatus", [0, 0, 0, 'collect_point_path'], "aamCaptureCurrRobotAndExJointStatus 采集点位", owner=self)
            # X轴正向移动
            send_request(self.ws_client, "simArcs.amStartJog", [0, 1, 0], "amStartJog 笛卡尔模式下朝X轴方向移动", owner=self)
            # 停止
            send_request(self.ws_client, "simArcs.amStopJog", [0], "amStopJog 停止转动", owner=self)
            # 在点位1前插入点位
            send_request(self.ws_client, "simArcs.aamInsertRobotAndExJointStatus", [0, 0, 0, 'collect_point_path', 1], "aamInsertRobotAndExJointStatus 插入点位", owner=self)
            # 在笛卡尔模式下朝Y轴方向移动
            send_request(self.ws_client, "simArcs.amStartJog",[0,2,0],"amStartJog 在笛卡尔模式下朝Y轴方向移动", owner=self)
            # 停止
            send_request(self.ws_client, "simArcs.amStopJog", [0], "amStopJog 停止转动", owner=self)
            # 替换点位0
            send_request(self.ws_client, "simArcs.aamReplaceRobotAndExJointStatus", [0, 0, 0, 'collect_point_path', 0], "aamReplaceRobotAndExJointStatus 替换点位", owner=self)
            # 点2轨迹回溯
            send_request(self.ws_client, "simArcs.aamTrajectoryBacktrackingPtpPose", [0, 0, 0, 'collect_point_path', 2, loadmodel_instance.loadObj_id, 100], "aamTrajectoryBacktrackingPtpPose 轨迹回溯", owner=self)


            # === 2. 点击生成程序流程 ===

            # 设置速率
            send_request(self.ws_client, "simArcs.aamSetSpeedRaitoOfPathPoint", 
                [0, 0, "collect_point_path", [{"point_index": i, "speed": 50} for i in range(3)]],
                "aamSetSpeedRaitoOfPathPoint 设置选中点位的速率", owner=self)

            # 设置运动模式
            send_request(self.ws_client, "simArcs.aamSetMoveModeOfPathPoint",
                [0, 0, "collect_point_path", [{"point_index": i, "move_mode": 0} for i in range(3)]],
                "aamSetMoveModeOfPathPoint 设置选中点位的运动模式", owner=self)

            # 设置平滑度
            send_request(self.ws_client, "simArcs.aamSetSlipPercentageOfPathPoint",
                [0, 0, "collect_point_path", [{"point_index": i, "slip_percentage": 50} for i in range(3)]],
                "aamSetSlipPercentageOfPathPoint 设置选中点位的平滑度百分比", owner=self)


            # [关键] 根据示教器采集的点位生成arl程序 - 需要获取返回值 arl_id
            # arcs_index机器人控制器索引、channel机器人通道名称、path_name采集路径的handle的字符串、loop循环次数、
            # capture_path_name生成程序名、arl_type程序的类型，0 创建出来的arl程序，1 覆盖原有的arl程序
            resp = send_request(self.ws_client, "simArcs.aamGenerateArlProgramFromRecords",
                [0, 0, "collect_point_path", 1, "program.arl", 0, [{"io_signal_groups": [{"io_index": -1, "io_type": -1, "io_status": True}]} for _ in range(3)]],
                "aamGenerateArlProgramFromRecords 根据示教器采集的点位生成arl程序", owner=self)
            if resp and resp.get("success") and resp.get("ret"):
                Teaching.arl_id = resp["ret"][0] # 获取ID赋值给局部变量
                logger.info(f"生成arl程序成功，对象ID：{Teaching.arl_id}")
                # 使用 arl_id 创建节点
                if Teaching.arl_id:
                    NewPoint(ws_client=self.ws_client, generateObj_id=Teaching.arl_id).ws_newpoint_chain()
                else:
                    logger.warning("arl_id 未生成，跳过创建节点")
            else:
                logger.warning(f"生成arl程序失败或返回为空：{resp}")


            # getall4
            GetAll4(ws_client=self.ws_client).ws_getall4_chain()


            # [关键] 创建示教点集 - 需要获取返回值 collect_point_path_id
            resp = send_request(self.ws_client, "simArcs.aamCreateTeachingPath", 
                ['program_data', 'collect_point_path', loadmodel_instance.loadObj_id], 
                "aamCreateTeachingPath 创建一条示教点集", owner=self)
            if resp and resp.get("success") and resp.get("ret"):
                Teaching.collect_point_path_id = resp["ret"][0] # 获取ID赋值给局部变量
                logger.info(f"创建示教点集成功，对象ID：{Teaching.collect_point_path_id}，我看看你类型{type(Teaching.collect_point_path_id)}")
                # 使用 collect_point_path_id 创建节点
                if Teaching.collect_point_path_id:
                    NewPoint(ws_client=self.ws_client,
                             generateObj_id=Teaching.collect_point_path_id).ws_newpoint_chain()
                else:
                    logger.warning("collect_point_path_id 未生成，跳过创建节点")
            else:
                logger.warning(f"创建示教点集失败或返回为空：{resp}")


            # getall4
            GetAll4(ws_client=self.ws_client).ws_getall4_chain()

            # 关闭示教器界面
            send_request(self.ws_client, "simArcs.aamStopPushMessageForTeachingPath", [], "aamStopPushMessageForTeachingPath 关闭示教器", owner=self)

            # 设置工件坐标系???
            send_request(self.ws_client, "simArcs.aamSetWobjToBaseTr", [0, 0, 'collect_point_path', -1], "aamSetWobjToBaseTr 设置工件坐标系", owner=self)


            # === 3. 编辑示教点集 ===

            # 获取当前采集示教点集
            send_request(self.ws_client, "simArcs.aamGetTeachingPath",[Teaching.collect_point_path_id],"aamGetTeachingPath 获取当前采集示教点集", owner=self)

            # 获取选择采集点集路径的坐标系类型
            send_request(self.ws_client, "simArcs.aamGetPathTipType",[0,0,str(Teaching.collect_point_path_id)],"aamGetPathTipType 获取选择采集点集路径的坐标系类型", owner=self)

            # 切换通道（使能状态下）
            # args arcs_index控制器索引，channel通道id，
            send_request(self.ws_client, "simArcs.amSwitchChannel",[0,0],"amSwitchChannel 切换通道", owner=self)

            # 设置工件坐标系和机器人base之间的pose（为什么每次打开示教器都要调用这个接口？？？？？）
            send_request(self.ws_client, "simArcs.aamSetWobjToBaseTr",[0,0,str(Teaching.collect_point_path_id),-1],"aamSetWobjToBaseTr 设置工件坐标系和机器人base之间的pose", owner=self)

            # 关闭示教器界面停止推流
            send_request(self.ws_client, "simArcs.aamStopPushMessageForTeachingPath",[],"aamStopPushMessageForTeachingPath 关闭示教器界面停止推流", owner=self)

            # 打开示教器界面开始推流
            send_request(self.ws_client, "simArcs.aamStartPushMessageForTeachingPath",[0,0,str(Teaching.collect_point_path_id)],"aamStartPushMessageForTeachingPath 打开示教器界面开始推流", owner=self)

            # 获取机器人仿真移动速率
            send_request(self.ws_client, "simArcs.amGetManuSpeed",[0,0],"amGetManuSpeed 获取移动速率", owner=self)

            # 获取轴模式
            send_request(self.ws_client, "simArcs.amGetManuAxisMode",[0],"amGetManuAxisMode 获取轴模式", owner=self)

            # 根据机器人句柄和路径名称得到工件坐标系的句柄
            send_request(self.ws_client, "simArcs.aamGetWobjHandleForTeachingPath",[0,0,str(Teaching.collect_point_path_id)],"aamGetWobjHandleForTeachingPath 根据机器人句柄和路径名称得到工件坐标系的句柄", owner=self)

            # 删除点位
            # arcs_index机器人控制器索引,channel机器人通道名称,point_index点位索引,路径名称
            send_request(self.ws_client, "simArcs.aamRemoveRobotAndExJointStatusRecord",[0,0,1,str(Teaching.collect_point_path_id)],"aamRemoveRobotAndExJointStatusRecord 删除点位", owner=self)

            # 设置采集点位的速率
            send_request(self.ws_client, "simArcs.aamSetSpeedRaitoOfPathPoint",
                              [0, 0, str(Teaching.collect_point_path_id), [{"point_index": i, "speed": 30} for i in range(2)]],
                              "aamSetSpeedRaitoOfPathPoint 设置选中点位的速率", owner=self)

            # 设置采集点位的运动模式
            send_request(self.ws_client, "simArcs.aamSetMoveModeOfPathPoint",
                              [0, 0, str(Teaching.collect_point_path_id), [{"point_index": i, "move_mode": 2} for i in range(2)]],
                              "aamSetMoveModeOfPathPoint 设置选中点位的运动模式", owner=self)

            # 设置采集点位的平滑度
            send_request(self.ws_client, "simArcs.aamSetSlipPercentageOfPathPoint",
                              [0, 0, str(Teaching.collect_point_path_id),
                               [{"point_index": i, "slip_percentage": 40} for i in range(2)]],
                              "aamSetSlipPercentageOfPathPoint 设置选中点位的平滑度百分比", owner=self)

            # 根据示教器采集的点位生成arl程序
            send_request(self.ws_client, "simArcs.aamGenerateArlProgramFromRecords",
                                     [0, 0, str(Teaching.collect_point_path_id), 1, "program.arl", 1,
                                      [{"io_signal_groups": [{"io_index": -1, "io_type": -1, "io_status": True}]} for _
                                       in range(2)]],
                                     "aamGenerateArlProgramFromRecords 根据示教器生成的点位生成arl程序", owner=self)

            # 在更新示教器界面的示教点集数据之后更新到左侧树
            send_request(self.ws_client,"simArcs.aamUpdateTeachingPath",
                         [Teaching.collect_point_path_id,str(Teaching.collect_point_path_id),loadmodel_instance.loadObj_id],
                         "aamUpdateTeachingPath 在更新示教器界面的示教点集数据之后更新到左侧树")

            # getall4


        except Exception as ex:
            logger.error(f"示教流程发生异常: {ex}")








