# @unittest_target("simArcs.amStartJog")
# @mock_response(
#     "simArcs.amStartJog",
#     success=False,
#     ret=["not enabled"]
# )
# def test_amStartJog_without_enable_should_fail(ws_client):
#     """
#     不调用任何 enable 接口
#     直接 jog
#     """
#     resp = send_request(
#         ws_client=ws_client,   # 真实 websocket-client
#         func="simArcs.amStartJog",
#         args=[0, 1, 1],
#         desc="jog without enable"
#     )
#
#     assert resp["success"] is False
