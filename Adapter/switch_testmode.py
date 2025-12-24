import os

def get_test_mode():
    """
    获取当前测试模式
    可选值: REAL (默认), UNIT, SANDBOX
    """
    return os.getenv("TEST_MODE", "REAL").upper()