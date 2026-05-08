import pytest
from core.request_invoker import send_request

# 普通夹具
@pytest.fixture
def jog_context(ws_client):
    # 固定流程：必须执行这 4 步，不能少也不能改
    send_request(ws_client, "simArcs.amStart", [0], "enable controller")
    send_request(ws_client, "simArcs.amSetEnableButtonState", [0, True], "req_amSetEnableButtonState 使能上电")
    send_request(ws_client, "simArcs.amSwitchChannel", [0, 0], "amSwitchChannel 切换通道")
    send_request(ws_client, "simArcs.aamStartPushMessageForTeachingPath", [0, 0, 'collect_point_path'], "StartPushMessage")
    return ws_client


# 工厂夹具（构建器）
@pytest.fixture
def jog_context_builder(ws_client):
    def build(
        do_start=True, start_args=[0],                              # 可以控制做不做、参数是什么
        do_enable=True, enable_args=[0, True],                      # 可以控制做不做、参数是什么
        do_switch=True, switch_args=[0, 0],                         # 可以控制做不做、参数是什么
        do_push=True, push_args=[0, 0, 'collect_point_path'],
    ):
        # 根据传入的参数，动态决定执行哪些步骤
        if do_start:        # 如果 do_start=False，就跳过步骤 1
            send_request(ws_client, "simArcs.amStart", start_args, "enable controller")
        if do_enable:       # 如果 enable_args=[0, None]，就用异常参数测试
            send_request(ws_client, "simArcs.amSetEnableButtonState", enable_args, "req_amSetEnableButtonState 使能上电")
        if do_switch:       # 如果 switch_args=[0, None]，就用异常参数测试
            send_request(ws_client, "simArcs.amSwitchChannel", switch_args, "amSwitchChannel 切换通道")
        if do_push:       # 如果 push_args=[0, None, None]，就用异常参数测试
            send_request(ws_client, "simArcs.aamStartPushMessageForTeachingPath", push_args, "StartPushMessage")
        return ws_client
    return build            # ← 关键：返回的是函数本身！

