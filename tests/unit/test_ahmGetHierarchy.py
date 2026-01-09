import pytest
from core.harness import send_request

def test_ahmGetHierarchy_with_full_context(ws_client, loadmodel_context_builder):
    """
    完整上下文：加载模型 -> 创建工作台/机器人节点 -> 设置父子关系
    目标接口：获取场景树
    """
    client = loadmodel_context_builder()
    resp = send_request(client, "simArcs.ahmGetHierarchy", [], "ahmGetHierarchy 获取场景树")
    assert resp.get("success") is True