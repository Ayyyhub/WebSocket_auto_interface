"""
AI 自动生成的 WebSocket 工作流测试用例
场景: loadmodel_chain
生成时间: 2026-05-08 15:11:57

本测试按工作流顺序链式调用所有接口，
后续接口的参数从前面接口的返回值中提取。
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from core.request_invoker import send_request


class TestLoadmodelChain:

    def test_workflow_happy_path(self, ws_client):
        """按工作流顺序执行所有接口，验证链式调用"""
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

        # Step 2: sim.getObjectPosition
        resp_2 = send_request(
            ws_client,
            "sim.getObjectPosition",
            [state.get("LoadModel.loadObj_id", -1), -1],
            "getObjectPosition 获取对象位置",
        )
        assert resp_2 is not None, f"Step 2 sim.getObjectPosition 返回为空"
        assert resp_2.get("success") == True, f"Step 2 sim.getObjectPosition 失败: {resp_2}"

        # Step 3: simArcs.webMoveObject
        resp_3 = send_request(
            ws_client,
            "simArcs.webMoveObject",
            [state.get("LoadModel.loadObj_id", -1), [0, 0, 0], -1, 4],
            "webMoveObject 对象移动",
        )
        assert resp_3 is not None, f"Step 3 simArcs.webMoveObject 返回为空"
        assert resp_3.get("success") == True, f"Step 3 simArcs.webMoveObject 失败: {resp_3}"

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

        # Step 6: simArcs.ahmSetElementParent
        resp_6 = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [state.get("workbench_point_id", -1), 0],
            "ahmSetElementParent1 设置工作台父节点",
        )
        assert resp_6 is not None, f"Step 6 simArcs.ahmSetElementParent 返回为空"
        assert resp_6.get("success") == True, f"Step 6 simArcs.ahmSetElementParent 失败: {resp_6}"

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

        # Step 8: simArcs.ahmSetElementParent
        resp_8 = send_request(
            ws_client,
            "simArcs.ahmSetElementParent",
            [state.get("robot_point_id", -1), state.get("workbench_point_id", -1)],
            "ahmSetElementParent 设置机器人的父节点",
        )
        assert resp_8 is not None, f"Step 8 simArcs.ahmSetElementParent 返回为空"
        assert resp_8.get("success") == True, f"Step 8 simArcs.ahmSetElementParent 失败: {resp_8}"

        # Step 9: simArcs.ahmGetHierarchy
        resp_9 = send_request(
            ws_client,
            "simArcs.ahmGetHierarchy",
            [],
            "ahmGetHierarchy 获取场景树",
        )
        assert resp_9 is not None, f"Step 9 simArcs.ahmGetHierarchy 返回为空"
        assert resp_9.get("success") == True, f"Step 9 simArcs.ahmGetHierarchy 失败: {resp_9}"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
