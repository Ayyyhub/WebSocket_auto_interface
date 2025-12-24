# 单测 mock

# 为什么一定要有 Adapter？
# 因为你现在最大的问题是：
# “单测到底该不该真的发 WS？”
# Adapter 的存在让你可以 推迟这个决定。
# 今天全 real
# 明天 mock
# 后天 sandbox
from utils.logger import logger
from tests.mock.mock_context import test_context

# 静态默认 Mock 数据 (兜底用)
DEFAULT_MOCK_DATA = {
    "simArcs.aamInitialize": {"success": True, "ret": ["Init_Success"], "id": "mock_init_id"},
    "simArcs.aamLoadModel": {"success": True, "ret": ["Model_Loaded_ID_123"], "id": "mock_load_id"},
    "simArcs.aamStart": {"success": True, "ret": [True], "id": "mock_start_id"},
    "simArcs.aamGenerateArlProgramFromRecords": {"success": True, "ret": ["ARL_PROG_ID_999"], "id": "mock_arl_id"},
    # Teaching Chain 相关默认 Mock
    "simArcs.aamCreateTeachingPath": {"success": True, "ret": ["Path_ID_001"], "id": "mock_path_id"},
    "simArcs.amStartJog": {"success": True, "ret": [], "id": "mock_jog_start"},
    "simArcs.amStopJog": {"success": True, "ret": [], "id": "mock_jog_stop"},
    "sim.loadModel": {"success": True, "ret": ["Obj_ID_Model_01"], "id": "mock_sim_load"},
}

def send_ws_mock(req, desc):
    """
    Mock 适配器核心逻辑
    优先级: Context Override > DEFAULT_MOCK_DATA > 通用成功响应
    """
    func_name = req.get("func")
    req_id = req.get("id")
    
    logger.info(f"[MOCK] 接口名称: {func_name} ,接口描述：{desc} ")

    # 1. 检查 Context 中是否有动态注入的 Mock 数据 (由 @mock_response 提供)
    override_resp = test_context.get_mock_override(func_name)
    if override_resp:
        override_resp["id"] = req_id  # 保持 ID 一致
        logger.info(f"[MOCK] 响应体: {override_resp}")
        return override_resp

    # ========================================================
    # 模拟真实行为 (Deep Mock Logic)
    # 如果没有强制覆盖返回值，我们在这里加入一些真实的参数校验逻辑
    # ========================================================
    
    if func_name == "simArcs.amStartJog":
        # 校验参数：axis_id (0-5), direction (0/1), speed (0-100)
        args = req.get("args", [])
        if len(args) < 3:
            logger.error("[MOCK] amStartJog 参数缺失")
            return {"success": False, "error": "Invalid arguments", "id": req_id}
            
        robot_index, axis_index, direction = args
        if axis_index > 5:
            logger.error(f"[MOCK] 轴索引 {axis_index} 超出范围 (0-5)")
            return {"success": False, "error": "Axis index out of range", "id": req_id}
            
        if direction not in [0, 1]:
            logger.error(f"[MOCK] 方向 {direction} 无效")
            return {"success": False, "error": "Invalid direction", "id": req_id}

        logger.info(f"[MOCK] amStartJog 校验通过: Axis={axis_index}, Dir={direction}")
        return {"success": True, "ret": [], "id": req_id}

    # ========================================================

    # 2. 检查静态默认 Mock 数据

    if func_name in DEFAULT_MOCK_DATA:
        resp = DEFAULT_MOCK_DATA[func_name].copy()
        resp["id"] = req_id
        logger.info(f"[MOCK] Hit Default Data: {resp}")
        return resp

    # 3. 兜底：返回通用成功响应
    logger.warning(f"[MOCK] No mock data found for {func_name}, returning generic success.")
    return {"success": True, "ret": [], "id": req_id}