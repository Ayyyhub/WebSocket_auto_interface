# #日志封装

from loguru import logger
import os
import sys  # 导入sys，用于控制台输出

# 使用全局变量确保处理器只被添加一次
_handlers_configured = False


"""配置日志处理器，确保只配置一次"""
def configure_logger():

    global _handlers_configured

    if _handlers_configured:
        return

    logger.remove()

    # 根据环境设置不同日志级别
    if os.getenv("ENVIRONMENT") == "DEBUG":
        log_level = "DEBUG"  # 开发环境记录详细日志
    else:
        log_level = "INFO"  # 生产环境只记录重要日志

    # 确保logs目录存在
    os.makedirs("Log/logs", exist_ok=True)

    # 用于文件归档
    logger.add(
        "Log/logs/ui_auto_test_{time:YYYY-MM-DD_HH-mm-ss}.log",
        rotation="1000 MB", # 这个1000MB是不是不太合理，如果我的日志多了超过1000了那不就糟了
        retention="3 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} |{module}:{function}:{line} - {message}",
        encoding="utf-8",
        enqueue=True,
    )

    # 控制台输出
    logger.add(
        sys.stderr,
        level=log_level,
        # 给不同字段加颜色标签
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{module}:{function}:{line}</cyan> - <level>{message}</level>",
        enqueue=True,
        colorize=True,  # 已开启，不用改
    )

    _handlers_configured = True


# 首次导入时自动配置
configure_logger()
logger = logger.bind(case="-",  step="-")

# 导出logger供全局使用
__all__ = ["logger"]
