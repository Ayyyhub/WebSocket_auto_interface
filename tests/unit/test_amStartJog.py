import pytest
from core.harness import send_request


def test_amStartJog_with_enable_should_success(ws_client, jog_context):
    """
    使用 jog_context 准备的正常流程上下文
    测试正常启动 JOG
    """
    resp = send_request(
        ws_client,
        "simArcs.amStartJog",
        [0, 1, 1],
        "start jog"
    )

    assert resp["success"] is True and resp["ret"] == [True], \
        f"断言失败：success={resp['success']}，ret={resp['ret']}"

def test_amStartJog_boundary_speed(ws_client, jog_context):
    """
    使用 jog_context 准备的正常流程上下文
    测试第三个参数异常情况
    """
    resp = send_request(
        ws_client,
        "simArcs.amStartJog",
        [0, 1, 100],
        "start jog with max speed"
    )
    assert resp["success"] is True and resp.get("ret") == [False], \
        f"断言失败：success={resp['success']}，ret={resp['ret']}"


@pytest.mark.parametrize(
    "do_start,do_enable,do_switch,do_push,expect_success",
    [
        (False, True,  True,  True,  True),
        (True,  False, True,  True,  True),
        (True,  True,  False, True,  True),
        (True,  True,  True,  False, True),
    ]
)
def test_jog_preconditions(ws_client, jog_context_builder, do_start, do_enable, do_switch, do_push, expect_success):
    client = jog_context_builder(
        do_start=do_start,
        do_enable=do_enable,
        do_switch=do_switch,
        do_push=do_push
    )
    resp = send_request(client, "simArcs.amStartJog", [0, 1, 1], "start jog")
    assert (resp.get("success") is True) == expect_success


@pytest.mark.parametrize(
    "enable_args,expect_success",
    [
        ([0, False], True),
        ([0, None],  True),
    ]
)
def test_jog_with_bad_enable(ws_client, jog_context_builder, enable_args, expect_success):
    # “带上下文的 ws_client ”
    client = jog_context_builder(enable_args=enable_args)
    resp = send_request(client, "simArcs.amStartJog", [0, 1, 1], "start jog")
    assert (resp.get("success") is True) == expect_success


@pytest.mark.parametrize(
    "jog_args,expect_success",
    [
        ([0, 6, 1], True),
        ([0, 1, 2], True),
        ([0, 1, 100], True),
    ]
)
def test_jog_with_bad_target_args(ws_client, jog_context_builder, jog_args, expect_success):
    # “带上下文的 ws_client ”
    client = jog_context_builder()
    resp = send_request(client, "simArcs.amStartJog", jog_args, "start jog")
    assert (resp.get("success") is True) == expect_success