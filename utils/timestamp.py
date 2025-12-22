import time

def get_unique_id(prefix: str) -> str:
    """
    生成带时间戳后缀的唯一ID
    :param prefix: ID前缀 (例如: "amStart")
    :return: 拼接了微秒时间戳的ID (例如: "amStart_1718899200123456")
    """
    return f"{prefix}_{int(time.time() * 1000000)}"