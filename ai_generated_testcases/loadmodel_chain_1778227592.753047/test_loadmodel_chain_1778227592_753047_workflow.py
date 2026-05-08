"""
AI 自动生成的 WebSocket 工作流测试用例
场景: loadmodel_chain_1778227592.753047
生成时间: 2026-05-08 16:08:24

包含:
  - test_workflow_happy_path: 按工作流顺序链式调用所有接口
  - 36 个变异测试: 在工作流上下文中注入异常参数
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.request_invoker import send_request


class TestLoadmodelChain1778227592753047:

    def _run_happy_path_to(self, ws_client, target_seq):
        """执行工作流步骤 1 到 target_seq-1，返回 state dict"""
        state = {}

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
            state["LoadModel.loadObj_id"] = resp_1["ret"][0]
        if target_seq <= 1:
            return state

        # Step 2: sim.getObjectPosition
        resp_2 = send_request(
            ws_client,
            "sim.getObjectPosition",
            [state.get("LoadModel.loadObj_id", -1), -1],
            "getObjectPosition 获取对象位置",
        )
        assert resp_2 is not None, f"Step 2 sim.getObjectPosition 返回为空"
        assert resp_2.get("success") == True, f"Step 2 sim.getObjectPosition 失败: {resp_2}"
        if target_seq <= 2:
            return state

        # Step 3: simArcs.webMoveObject
        resp_3 = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [state.get("LoadModel.loadObj_id", -1), [0, 0, 0], -1, 4],
            "webMoveObject 对象移动",
        )
        assert resp_3 is not None, f"Step 3 simArcs.webMoveObject 返回为空"
        assert resp_3.get("success") == True, f"Step 3 simArcs.webMoveObject 失败: {resp_3}"
        if target_seq <= 3:
            return state

        # Step 4: simArcs.webGetHandleType
        resp_4 = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [state.get("LoadModel.loadObj_id", -1)],
            "webGetHandleType 获取加载模型的handle类型",
        )
        assert resp_4 is not None, f"Step 4 simArcs.webGetHandleType 返回为空"
        assert resp_4.get("success") == True, f"Step 4 simArcs.webGetHandleType 失败: {resp_4}"
        if resp_4.get("ret"):
            state["loadObj_type"] = resp_4["ret"][0]
        if target_seq <= 4:
            return state

        # Step 5: simArcs.ahmCreateHierarchyElement
        resp_5 = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [0, 1],
            "ahmCreateHierarchyElement 创建工作台节点成功",
        )
        assert resp_5 is not None, f"Step 5 simArcs.ahmCreateHierarchyElement 返回为空"
        assert resp_5.get("success") == True, f"Step 5 simArcs.ahmCreateHierarchyElement 失败: {resp_5}"
        if resp_5.get("ret"):
            state["workbench_point_id"] = resp_5["ret"][0]
        if target_seq <= 5:
            return state

        # Step 6: simArcs.ahmSetElementParent
        resp_6 = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [state.get("workbench_point_id", -1), 0],
            "ahmSetElementParent1 设置工作台父节点",
        )
        assert resp_6 is not None, f"Step 6 simArcs.ahmSetElementParent 返回为空"
        assert resp_6.get("success") == True, f"Step 6 simArcs.ahmSetElementParent 失败: {resp_6}"
        if target_seq <= 6:
            return state

        # Step 7: simArcs.ahmCreateHierarchyElement
        resp_7 = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [state.get("LoadModel.loadObj_id", -1), state.get("loadObj_type", -1)],
            "ahmCreateHierarchyElement 创建机器人节点",
        )
        assert resp_7 is not None, f"Step 7 simArcs.ahmCreateHierarchyElement 返回为空"
        assert resp_7.get("success") == True, f"Step 7 simArcs.ahmCreateHierarchyElement 失败: {resp_7}"
        if resp_7.get("ret"):
            state["robot_point_id"] = resp_7["ret"][0]
        if target_seq <= 7:
            return state

        # Step 8: simArcs.ahmSetElementParent
        resp_8 = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [state.get("robot_point_id", -1), state.get("workbench_point_id", -1)],
            "ahmSetElementParent 设置机器人的父节点",
        )
        assert resp_8 is not None, f"Step 8 simArcs.ahmSetElementParent 返回为空"
        assert resp_8.get("success") == True, f"Step 8 simArcs.ahmSetElementParent 失败: {resp_8}"
        if target_seq <= 8:
            return state

        # Step 9: simArcs.ahmGetHierarchy
        resp_9 = send_request(
            ws_client,
            "simArcs.ahmGetHierarchy",
            [],
            "ahmGetHierarchy 获取场景树",
        )
        assert resp_9 is not None, f"Step 9 simArcs.ahmGetHierarchy 返回为空"
        assert resp_9.get("success") == True, f"Step 9 simArcs.ahmGetHierarchy 失败: {resp_9}"
        if target_seq <= 9:
            return state

        return state

    def test_workflow_happy_path(self, ws_client):
        """按工作流顺序执行所有接口，验证链式调用"""
        state = self._run_happy_path_to(ws_client, 10)
        assert state, '工作流执行完成但状态为空'

    def test_step1_loadModel_boundary_empty_path(self, ws_client):
        """Step 1 变异测试 [boundary]: 边界测试，模型路径为空字符串。"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [''],
            "loadModel 加载模型 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step1_loadModel_wrong_arg_type_path(self, ws_client):
        """Step 1 变异测试 [wrong_arg_type]: 传递错误类型参数，模型路径为整数。"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [12345],
            "loadModel 加载模型 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step1_loadModel_violation_insufficient_resources(self, ws_client):
        """Step 1 变异测试 [violation]: 违反业务规则，系统资源不足导致加载失败。"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [''],
            "loadModel 加载模型 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step1_loadModel_null_args(self, ws_client):
        """Step 1 变异测试 [null_args]: 参数传递为 null。"""
        resp = send_request(
            ws_client,
            "sim.loadModel",
            [None],
            "loadModel 加载模型 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step2_getObjectPosition_boundary_invalid_id(self, ws_client):
        """Step 2 变异测试 [boundary]: 边界测试，对象ID为负数。"""
        state = self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [0, -1],
            "getObjectPosition 获取对象位置 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step2_getObjectPosition_wrong_arg_type_id(self, ws_client):
        """Step 2 变异测试 [wrong_arg_type]: 传递错误类型参数，对象ID为字符串。"""
        state = self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            ['not_a_number', -1],
            "getObjectPosition 获取对象位置 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step2_getObjectPosition_violation_missing_loadModel(self, ws_client):
        """Step 2 变异测试 [violation]: 违反业务规则，未先调用 sim.loadModel。"""
        state = self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [-999, -1],
            "getObjectPosition 获取对象位置 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step2_getObjectPosition_null_args(self, ws_client):
        """Step 2 变异测试 [null_args]: 参数传递为 null。"""
        state = self._run_happy_path_to(ws_client, 2)
        resp = send_request(
            ws_client,
            "sim.getObjectPosition",
            [None, -1],
            "getObjectPosition 获取对象位置 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step3_webMoveObject_boundary_position_out_of_range(self, ws_client):
        """Step 3 变异测试 [boundary]: 边界测试，目标位置超出范围。"""
        state = self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [0, 0.0, -1, 0],
            "webMoveObject 对象移动 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step3_webMoveObject_wrong_arg_type_position(self, ws_client):
        """Step 3 变异测试 [wrong_arg_type]: 传递错误类型参数，目标位置为字符串。"""
        state = self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            ['not_a_number', 0.0, -1, 0],
            "webMoveObject 对象移动 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step3_webMoveObject_violation_missing_loadModel(self, ws_client):
        """Step 3 变异测试 [violation]: 违反业务规则，未先调用 sim.loadModel。"""
        state = self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [-999, 0.0, -1, 0],
            "webMoveObject 对象移动 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step3_webMoveObject_null_args(self, ws_client):
        """Step 3 变异测试 [null_args]: 参数传递为 null。"""
        state = self._run_happy_path_to(ws_client, 3)
        resp = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [None, 0.0, -1, 0],
            "webMoveObject 对象移动 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step4_webGetHandleType_boundary_invalid_id(self, ws_client):
        """Step 4 变异测试 [boundary]: 边界测试，对象ID为负数。"""
        state = self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [0],
            "webGetHandleType 获取加载模型的handle类型 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step4_webGetHandleType_wrong_arg_type_id(self, ws_client):
        """Step 4 变异测试 [wrong_arg_type]: 传递错误类型参数，对象ID为字符串。"""
        state = self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            ['not_a_number'],
            "webGetHandleType 获取加载模型的handle类型 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step4_webGetHandleType_violation_missing_loadModel(self, ws_client):
        """Step 4 变异测试 [violation]: 违反业务规则，未先调用 sim.loadModel。"""
        state = self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [-999],
            "webGetHandleType 获取加载模型的handle类型 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step4_webGetHandleType_null_args(self, ws_client):
        """Step 4 变异测试 [null_args]: 参数传递为 null。"""
        state = self._run_happy_path_to(ws_client, 4)
        resp = send_request(
            ws_client,
            "simArcs.webGetHandleType",
            [None],
            "webGetHandleType 获取加载模型的handle类型 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step5_ahmCreateHierarchyElement_boundary_invalid_parent_id(self, ws_client):
        """Step 5 变异测试 [boundary]: 边界测试，父节点ID为负数。"""
        state = self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [0, 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step5_ahmCreateHierarchyElement_wrong_arg_type_parent_id(self, ws_client):
        """Step 5 变异测试 [wrong_arg_type]: 传递错误类型参数，父节点ID为字符串。"""
        state = self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            ['not_a_number', 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step5_ahmCreateHierarchyElement_violation_missing_dependencies(self, ws_client):
        """Step 5 变异测试 [violation]: 违反业务规则，未先调用 sim.loadModel 或 simArcs.webGetHandleType。"""
        state = self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [-999, 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step5_ahmCreateHierarchyElement_null_args(self, ws_client):
        """Step 5 变异测试 [null_args]: 参数传递为 null。"""
        state = self._run_happy_path_to(ws_client, 5)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [None, 0],
            "ahmCreateHierarchyElement 创建工作台节点成功 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step6_ahmSetElementParent_boundary_workbench_point_id(self, ws_client):
        """Step 6 变异测试 [boundary]: 对 workbench_point_id 参数进行边界值测试"""
        state = self._run_happy_path_to(ws_client, 6)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [0, 0],
            "ahmSetElementParent1 设置工作台父节点 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == True, f"预期成功但失败: {resp}"

    def test_step6_ahmSetElementParent_wrong_arg_type_workbench_point_id(self, ws_client):
        """Step 6 变异测试 [wrong_arg_type]: workbench_point_id 参数类型错误，例如传入字符串"""
        state = self._run_happy_path_to(ws_client, 6)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            ['not_a_number', 0],
            "ahmSetElementParent1 设置工作台父节点 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step6_ahmSetElementParent_missing_workbench_point_id(self, ws_client):
        """Step 6 变异测试 [missing_args]: 缺少 workbench_point_id 参数"""
        state = self._run_happy_path_to(ws_client, 6)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [0],
            "ahmSetElementParent1 设置工作台父节点 [missing_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step6_ahmSetElementParent_violation_invalid_workbench_point_id(self, ws_client):
        """Step 6 变异测试 [violation]: 传入无效的 workbench_point_id，例如负数"""
        state = self._run_happy_path_to(ws_client, 6)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [-999, 0],
            "ahmSetElementParent1 设置工作台父节点 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step6_ahmSetElementParent_null_workbench_point_id(self, ws_client):
        """Step 6 变异测试 [null_args]: workbench_point_id 参数传 null"""
        state = self._run_happy_path_to(ws_client, 6)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [None, 0],
            "ahmSetElementParent1 设置工作台父节点 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step7_ahmCreateHierarchyElement_boundary_loadObj_id(self, ws_client):
        """Step 7 变异测试 [boundary]: 对 loadObj_id 参数进行边界值测试"""
        state = self._run_happy_path_to(ws_client, 7)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [0, 0],
            "ahmCreateHierarchyElement 创建机器人节点 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == True, f"预期成功但失败: {resp}"

    def test_step7_ahmCreateHierarchyElement_wrong_arg_type_loadObj_id(self, ws_client):
        """Step 7 变异测试 [wrong_arg_type]: loadObj_id 参数类型错误，例如传入字符串"""
        state = self._run_happy_path_to(ws_client, 7)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            ['not_a_number', 0],
            "ahmCreateHierarchyElement 创建机器人节点 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step7_ahmCreateHierarchyElement_missing_loadObj_id(self, ws_client):
        """Step 7 变异测试 [missing_args]: 缺少 loadObj_id 参数"""
        state = self._run_happy_path_to(ws_client, 7)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [0],
            "ahmCreateHierarchyElement 创建机器人节点 [missing_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step7_ahmCreateHierarchyElement_violation_invalid_loadObj_id(self, ws_client):
        """Step 7 变异测试 [violation]: 传入无效的 loadObj_id，例如负数"""
        state = self._run_happy_path_to(ws_client, 7)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [-999, 0],
            "ahmCreateHierarchyElement 创建机器人节点 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step7_ahmCreateHierarchyElement_null_loadObj_id(self, ws_client):
        """Step 7 变异测试 [null_args]: loadObj_id 参数传 null"""
        state = self._run_happy_path_to(ws_client, 7)
        resp = send_request(
            ws_client,
            "simArcs.ahmCreateHierarchyElement",
            [None, 0],
            "ahmCreateHierarchyElement 创建机器人节点 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step8_ahmSetElementParent_robot_boundary_robot_point_id(self, ws_client):
        """Step 8 变异测试 [boundary]: 对 robot_point_id 参数进行边界值测试"""
        state = self._run_happy_path_to(ws_client, 8)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [0, 0],
            "ahmSetElementParent 设置机器人的父节点 [boundary]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == True, f"预期成功但失败: {resp}"

    def test_step8_ahmSetElementParent_robot_wrong_arg_type_robot_point_id(self, ws_client):
        """Step 8 变异测试 [wrong_arg_type]: robot_point_id 参数类型错误，例如传入字符串"""
        state = self._run_happy_path_to(ws_client, 8)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            ['not_a_number', 0],
            "ahmSetElementParent 设置机器人的父节点 [wrong_arg_type]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step8_ahmSetElementParent_robot_missing_robot_point_id(self, ws_client):
        """Step 8 变异测试 [missing_args]: 缺少 robot_point_id 参数"""
        state = self._run_happy_path_to(ws_client, 8)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [0],
            "ahmSetElementParent 设置机器人的父节点 [missing_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step8_ahmSetElementParent_robot_violation_invalid_robot_point_id(self, ws_client):
        """Step 8 变异测试 [violation]: 传入无效的 robot_point_id，例如负数"""
        state = self._run_happy_path_to(ws_client, 8)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [-999, 0],
            "ahmSetElementParent 设置机器人的父节点 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step8_ahmSetElementParent_robot_null_robot_point_id(self, ws_client):
        """Step 8 变异测试 [null_args]: robot_point_id 参数传 null"""
        state = self._run_happy_path_to(ws_client, 8)
        resp = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [None, 0],
            "ahmSetElementParent 设置机器人的父节点 [null_args]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"

    def test_step9_ahmGetHierarchy_system_violation(self, ws_client):
        """Step 9 变异测试 [violation]: 系统状态异常，无法获取场景树"""
        state = self._run_happy_path_to(ws_client, 9)
        resp = send_request(
            ws_client,
            "simArcs.ahmGetHierarchy",
            [],
            "ahmGetHierarchy 获取场景树 [violation]",
        )
        assert resp is not None, '接口返回为空'
        assert resp.get("success") == False, f"预期失败但成功: {resp}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
