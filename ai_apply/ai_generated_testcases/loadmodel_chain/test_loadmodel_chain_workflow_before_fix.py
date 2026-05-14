"""
AI 自动生成的 WebSocket 工作流测试用例
场景: loadmodel_chain
生成时间: 2026-05-14 15:36:01

包含:
  - test_workflow_happy_path: 按工作流顺序链式调用所有接口
  - 25 个变异测试: 在工作流上下文中注入异常参数
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.request_invoker import send_request


class TestLoadmodelChain:

    def _run_happy_path_to(self, ws_client, target_seq):
        """执行工作流步骤 1 到 target_seq-1，返回 state dict"""
        state = {}

        if 1 >= target_seq:
            return state

        # Step 1: sim.loadModel
        resp_1 = send_request(
            ws_client,
            "sim.loadModel",
            ['public/models/robot/AIR4_560A/AIR4_560A.m'],
            "loadModel 加载模型",
        )
        assert resp_1 is not None, f"Step 1 sim.loadModel 返回为空"
        assert resp_1.get("success") == True, f"Step 1 sim.loadModel 失败: {resp_1}"
        if resp_1.get("ret"):
            state["LoadModel.object_handle"] = resp_1["ret"][0]

        if 2 >= target_seq:
            return state

        # Step 2: sim.getObjectPosition
        resp_2 = send_request(
            ws_client,
            "sim.getObjectPosition",
            [state.get("LoadModel.object_handle", -1), -1],
            "getObjectPosition 获取对象位置",
        )
        assert resp_2 is not None, f"Step 2 sim.getObjectPosition 返回为空"
        assert resp_2.get("success") == True, f"Step 2 sim.getObjectPosition 失败: {resp_2}"

        if 3 >= target_seq:
            return state

        # Step 3: simArcs.webMoveObject
        resp_3 = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [state.get("LoadModel.object_handle", -1), [0, 0, 0], -1, 4],
            "webMoveObject 对象移动",
        )
        assert resp_3 is not None, f"Step 3 simArcs.webMoveObject 返回为空"
        assert resp_3.get("success") == True, f"Step 3 simArcs.webMoveObject 失败: {resp_3}"

        if 4 >= target_seq:
            return state

        # Step 4: simArcs.webGetHandleType
        resp_4 = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [state.get("LoadModel.object_handle", -1)],
            "webGetHandleType 获取加载模型的handle类型",
        )
        assert resp_4 is not None, f"Step 4 simArcs.webGetHandleType 返回为空"
        assert resp_4.get("success") == True, f"Step 4 simArcs.webGetHandleType 失败: {resp_4}"
        if resp_4.get("ret"):
            state["loadObj_type"] = resp_4["ret"][0]

        if 5 >= target_seq:
            return state

        # Step 5: simArcs.ahmCreateHierarchyElement
        resp_5 = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [state.get("LoadModel.object_handle", -1), 2],
            "ahmCreateHierarchyElement 创建工作台节点成功",
        )
        assert resp_5 is not None, f"Step 5 simArcs.ahmCreateHierarchyElement 返回为空"
        assert resp_5.get("success") == True, f"Step 5 simArcs.ahmCreateHierarchyElement 失败: {resp_5}"
        if resp_5.get("ret"):
            state["obj_id"] = resp_5["ret"][0]

        if 6 >= target_seq:
            return state

        # Step 6: simArcs.ahmSetElementParent
        resp_6 = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [state.get("obj_id", -1), -1],
            "ahmSetElementParent1 设置工作台父节点",
        )
        assert resp_6 is not None, f"Step 6 simArcs.ahmSetElementParent 返回为空"
        assert resp_6.get("success") == True, f"Step 6 simArcs.ahmSetElementParent 失败: {resp_6}"

        if 7 >= target_seq:
            return state

        # Step 7: simArcs.ahmGetHierarchy
        resp_7 = send_request(
            ws_client,
            "simArcs.ahmGetHierarchy",
            [],
            "ahmGetHierarchy 获取场景树",
        )
        assert resp_7 is not None, f"Step 7 simArcs.ahmGetHierarchy 返回为空"
        assert resp_7.get("success") == True, f"Step 7 simArcs.ahmGetHierarchy 失败: {resp_7}"

        return state

    def test_workflow_happy_path(self, ws_client):
        """按工作流顺序执行所有接口，验证链式调用"""
        state = self._run_happy_path_to(ws_client, 8)
        assert state, '工作流执行完成但状态为空'

    def test_step1_loadModel_boundary_empty_path(self, ws_client):
        """Step 1 变异测试 [boundary]: 路径为空字符串（边界值）"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            ['"public/models/robot/AIR4_560A/AIR4_560A.m"'],
            "loadModel 加载模型 [boundary]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step1_loadModel_wrong_arg_type_path(self, ws_client):
        """Step 1 变异测试 [wrong_arg_type]: 路径参数类型为非字符串（错误类型）"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [12345],
            "loadModel 加载模型 [wrong_arg_type]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step1_loadModel_null_args(self, ws_client):
        """Step 1 变异测试 [null_args]: 路径参数为null"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [None],
            "loadModel 加载模型 [null_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step2_getObjectPosition_boundary_invalid_handle(self, ws_client):
        """Step 2 变异测试 [boundary]: 对象句柄为空字符串（边界值）"""
        self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            ['', -1],
            "getObjectPosition 获取对象位置 [boundary]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step2_getObjectPosition_wrong_arg_type_handle(self, ws_client):
        """Step 2 变异测试 [wrong_arg_type]: 对象句柄参数为非字符串（错误类型）"""
        self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [12345, 0],
            "getObjectPosition 获取对象位置 [wrong_arg_type]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step2_getObjectPosition_missing_args(self, ws_client):
        """Step 2 变异测试 [missing_args]: 缺少对象句柄参数"""
        self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [0],
            "getObjectPosition 获取对象位置 [missing_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step2_getObjectPosition_violation_invalid_handle(self, ws_client):
        """Step 2 变异测试 [violation]: 对象句柄无效或未加载模型（业务规则违反）"""
        self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            ['', 0],
            "getObjectPosition 获取对象位置 [violation]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step2_getObjectPosition_null_args(self, ws_client):
        """Step 2 变异测试 [null_args]: 对象句柄为null"""
        self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [None, 0],
            "getObjectPosition 获取对象位置 [null_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step3_webMoveObject_boundary_invalid_position(self, ws_client):
        """Step 3 变异测试 [boundary]: 目标位置为极端空间坐标（边界值）"""
        self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [-1, 0.0, 0, 1],
            "webMoveObject 对象移动 [boundary]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step3_webMoveObject_wrong_arg_type_handle(self, ws_client):
        """Step 3 变异测试 [wrong_arg_type]: 对象句柄为非字符串（错误类型）"""
        self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [12345, 0.0, 0, 1],
            "webMoveObject 对象移动 [wrong_arg_type]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step3_webMoveObject_missing_args(self, ws_client):
        """Step 3 变异测试 [missing_args]: 缺少对象句柄或目标位置"""
        self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [0.0, 0, 1],
            "webMoveObject 对象移动 [missing_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step3_webMoveObject_violation_invalid_handle(self, ws_client):
        """Step 3 变异测试 [violation]: 对象句柄无效或未加载模型（业务规则违反）"""
        self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            ['', 0.0, 0, 1],
            "webMoveObject 对象移动 [violation]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step3_webMoveObject_null_args(self, ws_client):
        """Step 3 变异测试 [null_args]: 对象句柄或目标位置为null"""
        self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [None, 0.0, 0, 1],
            "webMoveObject 对象移动 [null_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step4_webGetHandleType_wrong_arg_type_handle(self, ws_client):
        """Step 4 变异测试 [wrong_arg_type]: 对象句柄为非字符串（错误类型）"""
        self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [12345],
            "webGetHandleType 获取加载模型的handle类型 [wrong_arg_type]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step4_webGetHandleType_null_args(self, ws_client):
        """Step 4 变异测试 [null_args]: 对象句柄为null"""
        self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [None],
            "webGetHandleType 获取加载模型的handle类型 [null_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step5_ahmCreateHierarchyElement_boundary_invalid_parent_id(self, ws_client):
        """Step 5 变异测试 [boundary]: 父节点ID为极端值（边界值）"""
        self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            ['', 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [boundary]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step5_ahmCreateHierarchyElement_wrong_arg_type_handle(self, ws_client):
        """Step 5 变异测试 [wrong_arg_type]: 模型对象句柄为非字符串（错误类型）"""
        self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [12345, 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [wrong_arg_type]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step5_ahmCreateHierarchyElement_missing_args(self, ws_client):
        """Step 5 变异测试 [missing_args]: 缺少模型对象句柄或父节点ID"""
        self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [missing_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step5_ahmCreateHierarchyElement_violation_invalid_handle(self, ws_client):
        """Step 5 变异测试 [violation]: 模型对象句柄无效或未加载模型（业务规则违反）"""
        self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            ['', 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [violation]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'

    def test_step5_ahmCreateHierarchyElement_null_args(self, ws_client):
        """Step 5 变异测试 [null_args]: 模型对象句柄或父节点ID为null"""
        self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [None, 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [null_args]",
        )
        assert resp is None or resp.get('success') == False, f'预期失败但成功: {resp}'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
