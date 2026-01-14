# Locust UI界面压测的持续时间
import os
import sys
from locust import events
import gevent

# $env:LOCUST_AUTO_STOP = "60"  # 在终端设置压测持续时间为60秒

AUTO_STOP_AFTER_SECONDS = int(os.getenv("LOCUST_AUTO_STOP", "0"))  # 0 表示关闭

def _stop_locust(environment):
    if environment.runner:
        print(f"\n⏰ {AUTO_STOP_AFTER_SECONDS}秒已到，正在停止压测...\n")
        
        try:
            # 先手动触发 test_stop 事件（确保导出报告）
            events.test_stop.fire(environment=environment)
        except Exception as e:
            print(f"⚠️ test_stop 事件处理异常: {e}")
        
        # 给一些时间让事件处理完成
        gevent.sleep(1)
        
        # 再调用 quit()
        environment.runner.quit()
        
        # 给 2 秒时间让 Locust 正常清理
        gevent.sleep(2)
        
        # 2 秒后强制退出
        print("\n🔴 强制退出 Locust 进程\n")
        sys.exit(0)

def _schedule_autostop(environment, **kwargs):
    if AUTO_STOP_AFTER_SECONDS > 0:
        gevent.spawn_later(AUTO_STOP_AFTER_SECONDS, _stop_locust, environment)

events.test_start.add_listener(_schedule_autostop)