import pytest
from core.harness import send_request


@pytest.fixture
def jog_context(ws_client):
    send_request(ws_client, "simArcs.amStart", [0], "enable controller")
    send_request(ws_client, "simArcs.amSetEnableButtonState", [0, True], "req_amSetEnableButtonState 使能上电")
    send_request(ws_client, "simArcs.amSwitchChannel", [0, 0], "amSwitchChannel 切换通道")
    send_request(ws_client, "simArcs.aamStartPushMessageForTeachingPath", [0, 0, 'collect_point_path'], "StartPushMessage")
    return ws_client


@pytest.fixture
def jog_context_builder(ws_client):
    def build(
        do_start=True, start_args=[0],
        do_enable=True, enable_args=[0, True],
        do_switch=True, switch_args=[0, 0],
        do_push=True, push_args=[0, 0, 'collect_point_path'],
    ):
        if do_start:
            send_request(ws_client, "simArcs.amStart", start_args, "enable controller")
        if do_enable:
            send_request(ws_client, "simArcs.amSetEnableButtonState", enable_args, "req_amSetEnableButtonState 使能上电")
        if do_switch:
            send_request(ws_client, "simArcs.amSwitchChannel", switch_args, "amSwitchChannel 切换通道")
        if do_push:
            send_request(ws_client, "simArcs.aamStartPushMessageForTeachingPath", push_args, "StartPushMessage")
        return ws_client
    return build

