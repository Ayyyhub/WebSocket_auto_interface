from core.harness import send_request

""" 执行1-15号初始化接口 """

def ws_init_chain(ws_client):
    
    # 1-15号接口
    # 1. 加载后端simArcs的入口
    send_request(ws_client, "wsRemoteApi.require", ["simArcs", "simAssimp", "simStepOrIges", "simIK"], "wsRemoteApi.require 加载后端simArcs的入口")
    
    # 2. 获取所有场景（新）
    send_request(ws_client, "simArcs.webGetAllSceneNames", [], "webGetAllSceneNames 获取所有场景")
    
    # 3. 当前场景id
    send_request(ws_client, "sim.getSelectedSceneID", [], "getSelectedSceneID 当前场景id")
    
    # 4. 切换场景
    send_request(ws_client, "sim.switchToScene", [0], "switchToScene 切换场景")
    
    # 5. 获取所有坐标信息
    send_request(ws_client, "simArcs.afmGetAll", [], "afmGetAll 获取所有坐标信息")
    
    # 6. 获取机器人配置
    send_request(ws_client, "simArcs.rmGetAll", [], "rmGetAll 获取机器人配置")
    
    # 7. 获取所有控制器
    send_request(ws_client, "simArcs.amGetAll", [], "amGetAll 获取所有控制器")
    
    # 8. 获取所有arl程序信息
    send_request(ws_client, "simArcs.aamGetAll", [], "aamGetAll 获取所有arl程序信息")
    
    # 9. 重新构建树
    send_request(ws_client, "simArcs.ahmRebuildHierarchy", [], "ahmRebuildHierarchy 重新构建树")
    
    # 10. 获取场景树
    send_request(ws_client, "simArcs.ahmGetHierarchy", [], "ahmGetHierarchy 获取场景树")
    
    # 11. 获取所有外部轴信息
    send_request(ws_client, "simArcs.ejmGetAll", [], "ejmGetAll 获取所有外部轴信息")
    
    # 12. 得到当前场景中信号的属性信息
    send_request(ws_client, "simArcs.iomGetAllIOSignalActions", [], "iomGetAllIOSignalActions 得到当前场景中信号的属性信息")
    
    # 13. 获取所有控制器
    send_request(ws_client, "simArcs.amGetAll", [], "amGetAll_2 获取所有控制器")
    
    # 14. 获取可视化仿真状态
    send_request(ws_client, "simArcs.amGetVisualSimulationState", [], "amGetVisualSimulationState 获取可视化仿真状态")
    
    # 15. 获取碰撞检测状态
    send_request(ws_client, "simArcs.webGetCollisionDetectionStatus", [], "webGetCollisionDetectionStatus 获取碰撞检测状态")



