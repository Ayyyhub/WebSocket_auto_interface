from core.ws_request import ws_send_and_wait

""" 执行1-15号初始化接口 """

def ws_init_chain(ws_client):
    
    # 1-15号接口
    # 1. 加载后端simArcs的入口（第一次调用可能触发后端冷启动，给更长的等待时间和重试次数）
    ws_send_and_wait(
        {"func": "wsRemoteApi.require", "args": ["simArcs", "simAssimp", "simStepOrIges", "simIK"], "id": "require"},
        "wsRemoteApi.require 加载后端simArcs的入口",
        ws_client=ws_client,
    )
    # 2. 获取所有场景（新）
    ws_send_and_wait({"func": "simArcs.webGetAllSceneNames", "args": [], "id": "webGetAllSceneNames"}, "webGetAllSceneNames 获取所有场景",ws_client=ws_client)
    # 3. 当前场景id
    ws_send_and_wait({"func": "sim.getSelectedSceneID", "id": "getSelectedSceneID"}, "getSelectedSceneID 当前场景id",ws_client=ws_client)
    # 4. 切换场景
    ws_send_and_wait({"func": "sim.switchToScene", "args": [0], "id": "switchToScene"}, "switchToScene 切换场景",ws_client=ws_client)
    # 5. 获取所有坐标信息
    ws_send_and_wait({"func": "simArcs.afmGetAll", "id": "afmGetAll"}, "afmGetAll 获取所有坐标信息",ws_client=ws_client)
    # 6. 获取机器人配置
    ws_send_and_wait({"func": "simArcs.rmGetAll", "args": [], "id": "rmGetAll"}, "rmGetAll 获取机器人配置",ws_client=ws_client)
    # 7. 获取所有控制器
    ws_send_and_wait({"func": "simArcs.amGetAll", "args": [], "id": "amGetAll"}, "amGetAll 获取所有控制器",ws_client=ws_client)
    # 8. 获取所有arl程序信息
    ws_send_and_wait({"func": "simArcs.aamGetAll", "args": [], "id": "aamGetAll"}, "aamGetAll 获取所有arl程序信息",ws_client=ws_client)
    # 9. 重新构建树
    ws_send_and_wait({"func": "simArcs.ahmRebuildHierarchy", "args": [], "id": "ahmRebuildHierarchy"}, "ahmRebuildHierarchy 重新构建树",ws_client=ws_client)
    # 10. 获取场景树
    ws_send_and_wait({"func": "simArcs.ahmGetHierarchy", "args": [], "id": "ahmGetHierarchy"}, "ahmGetHierarchy 获取场景树",ws_client=ws_client)
    # 11. 获取所有外部轴信息（为什么要调用这个接口呢，是不是不太合理呢？）
    ws_send_and_wait({"func": "simArcs.ejmGetAll", "args": [], "id": "ejmGetAll"}, "ejmGetAll 获取所有外部轴信息",ws_client=ws_client)
    # 12. 得到当前场景中信号的属性信息
    ws_send_and_wait({"func": "simArcs.iomGetAllIOSignalActions", "id": "iomGetAllIOSignalActions"}, "iomGetAllIOSignalActions 得到当前场景中信号的属性信息",ws_client=ws_client)
    # 13. 获取所有控制器
    ws_send_and_wait({"func": "simArcs.amGetAll", "args": [], "id": "amGetAll_2"}, "amGetAll_2 获取所有控制器",ws_client=ws_client)
    # 14. 获取可视化仿真状态
    ws_send_and_wait({"func": "simArcs.amGetVisualSimulationState", "args": [], "id": "amGetVisualSimulationState"}, "amGetVisualSimulationState 获取可视化仿真状态",ws_client=ws_client)
    # 15. 获取碰撞检测状态
    ws_send_and_wait({"func": "simArcs.webGetCollisionDetectionStatus","args":[], "id": "webGetCollisionDetectionStatus"}, "webGetCollisionDetectionStatus 获取碰撞检测状态",ws_client=ws_client)

    # # 16. 获取全局bool属性
    # safe_ws_call({"func":"sim.getBoolParam","args":[],"id":"getBoolParam"}, "getBoolParam")



