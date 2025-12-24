from functools import wraps
from tests.mock.mock_context import test_context

# 职责：
# 在 send_request 被调用时
# 判断：
# 当前是否处于 unit test
# 当前接口是否是目标接口
# 动态覆盖 get_test_mode() 的结果


def unittest_target(func_name):
    """
    装饰器：标记当前测试用例的主要目标接口
    
    Usage:
    @unittest_target("simArcs.amStart")
    def test_am_start_workflow(self):
        ...
    """
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **kwargs):
            # 1. 设置上下文 [关键]
            # 等价于 self.local.target = "simArcs.amStartJog"
            test_context.current_target = func_name
            try:
                # 2. 执行测试用例
                return test_func(*args, **kwargs)
            finally:
                # 3. 清理上下文 (防止污染下一个用例)
                test_context.clear()
        return wrapper
    return decorator


def mock_response(func_name, success=True, ret=None, **kwargs):
    """
    装饰器：定义特定接口的 Mock 行为
    
    Usage:
    @mock_response("simArcs.aamInitialize", success=True, ret=["Init_OK"])
    def test_init(self):
        ...
    """
    def decorator(test_func):
        @wraps(test_func)
        def wrapper(*args, **inner_kwargs):
            # 构造标准响应格式
            expected_resp = {
                "success": success,
                "ret": ret if ret is not None else [],
                "id": kwargs.get("id", "mock_id_auto")
            }
            # 注入上下文 [关键]
            # 等价于--当前测试线程.local.overrides["simArcs.amStartJog"] = {
            #       "success": True,
            #       "ret": [],
            #       "id": "mock_id_auto"
            # }
            test_context.set_mock_override(func_name, expected_resp)
            return test_func(*args, **inner_kwargs)
        return wrapper
    return decorator



# @unittest_target("simArcs.amStart")
# @mock_response("simArcs.aamInitialize", success=True) # 强制 Init 成功
# @mock_response("simArcs.amStart", success=False)      # 强制 Start 失败，测试异常处理
# def test_start_failure(self):
#     ...