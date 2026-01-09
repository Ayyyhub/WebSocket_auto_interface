import pytest
from core.harness import send_request

@pytest.fixture
def loadmodel_context(ws_client):
    resp_load = send_request(ws_client, "sim.loadModel", ["public/models/robot/AIR4_560A/AIR4_560A.m"], "loadModel")
    loadObj_id = resp_load["ret"][0] if resp_load and isinstance(resp_load, dict) else None

    if loadObj_id is not None:
        send_request(ws_client, "sim.getObjectPosition", [loadObj_id, -1], "getObjectPosition")
        send_request(ws_client, "simArcs.webMoveObject", [loadObj_id, [0, 0, 0], -1, 4], "webMoveObject")
        resp_handle = send_request(ws_client, "simArcs.webGetHandleType", [loadObj_id], "webGetHandleType")
        loadObj_type = resp_handle["ret"][0] if resp_handle and isinstance(resp_handle, dict) else None
        resp_w1 = send_request(ws_client, "simArcs.ahmCreateHierarchyElement", [0, 1], "ahmCreateHierarchyElement1")
        workbench_point_id = resp_w1["ret"][0] if resp_w1 and isinstance(resp_w1, dict) else None
        if workbench_point_id is not None:
            send_request(ws_client, "simArcs.ahmSetElementParent", [workbench_point_id, 0], "ahmSetElementParent1")
        if loadObj_type is not None:
            resp_w2 = send_request(ws_client, "simArcs.ahmCreateHierarchyElement", [loadObj_id, loadObj_type], "ahmCreateHierarchyElement2")
            robot_point_id = resp_w2["ret"][0] if resp_w2 and isinstance(resp_w2, dict) else None
            if robot_point_id is not None and workbench_point_id is not None:
                send_request(ws_client, "simArcs.ahmSetElementParent", [robot_point_id, workbench_point_id], "ahmSetElementParent2")
    return ws_client

@pytest.fixture
def loadmodel_context_builder(ws_client):
    def build(
        do_loadmodel=True, loadmodel_args=["public/models/robot/AIR4_560A/AIR4_560A.m"],
        do_getObjectPosition=True, getObjectPosition_args=None,
        do_webMoveObject=True, webMoveObject_args=None,
        do_webGetHandleType=True, webGetHandleType_args=None,
        do_ahmCreateHierarchyElement1=True, ahmCreateHierarchyElement1_args=[0, 1],
        do_ahmSetElementParent1=True, ahmSetElementParent1_args=None,
        do_ahmCreateHierarchyElement2=True, ahmCreateHierarchyElement2_args=None,
        do_ahmSetElementParent2=True, ahmSetElementParent2_args=None,
    ):
        loadObj_id = None
        loadObj_type = None
        workbench_point_id = None
        if do_loadmodel:
            resp = send_request(ws_client, "sim.loadModel", loadmodel_args, "loadModel")
            loadObj_id = resp["ret"][0] if resp and isinstance(resp, dict) else None
        if do_getObjectPosition and loadObj_id is not None:
            args = getObjectPosition_args or [loadObj_id, -1]
            send_request(ws_client, "sim.getObjectPosition", args, "getObjectPosition")
        if do_webMoveObject and loadObj_id is not None:
            args = webMoveObject_args or [loadObj_id, [0, 0, 0], -1, 4]
            send_request(ws_client, "simArcs.webMoveObject", args, "webMoveObject")
        if do_webGetHandleType and loadObj_id is not None:
            args = webGetHandleType_args or [loadObj_id]
            resp = send_request(ws_client, "simArcs.webGetHandleType", args, "webGetHandleType")
            loadObj_type = resp["ret"][0] if resp and isinstance(resp, dict) else None
        if do_ahmCreateHierarchyElement1:
            resp = send_request(ws_client, "simArcs.ahmCreateHierarchyElement", ahmCreateHierarchyElement1_args, "ahmCreateHierarchyElement1")
            workbench_point_id = resp["ret"][0] if resp and isinstance(resp, dict) else None
        if do_ahmSetElementParent1 and workbench_point_id is not None:
            args = ahmSetElementParent1_args or [workbench_point_id, 0]
            send_request(ws_client, "simArcs.ahmSetElementParent", args, "ahmSetElementParent1")
        if do_ahmCreateHierarchyElement2 and loadObj_id is not None and loadObj_type is not None:
            args = ahmCreateHierarchyElement2_args or [loadObj_id, loadObj_type]
            resp = send_request(ws_client, "simArcs.ahmCreateHierarchyElement", args, "ahmCreateHierarchyElement2")
            robot_point_id = resp["ret"][0] if resp and isinstance(resp, dict) else None
            if do_ahmSetElementParent2 and robot_point_id is not None and workbench_point_id is not None:
                args = ahmSetElementParent2_args or [robot_point_id, workbench_point_id]
                send_request(ws_client, "simArcs.ahmSetElementParent", args, "ahmSetElementParent2")
        return ws_client
    return build
