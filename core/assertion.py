

def assert_resp_true(resp):
    if not isinstance(resp, dict):
        raise AssertionError(f"响应结果不是 dict: {type(resp)} {resp}")

    if "success" not in resp:
        raise AssertionError(f"响应结果缺少 success: {resp}")

    if not resp["success"]:
        return False

    if "ret" not in resp:
        raise AssertionError(f"响应结果缺少 ret: {resp}")

    return True



