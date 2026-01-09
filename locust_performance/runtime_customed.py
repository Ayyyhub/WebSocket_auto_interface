# Locust UI界面压测的持续时间
import os
from locust import events
import gevent

# $env:LOCUST_AUTO_STOP = "60"  # 在终端设置压测持续时间为60秒

AUTO_STOP_AFTER_SECONDS = int(os.getenv("LOCUST_AUTO_STOP", "0"))  # 0 表示关闭

def _stop_locust(environment):
    if environment.runner:
        environment.runner.quit()

def _schedule_autostop(environment, **kwargs):
    if AUTO_STOP_AFTER_SECONDS > 0:
        gevent.spawn_later(AUTO_STOP_AFTER_SECONDS, _stop_locust, environment)

events.test_start.add_listener(_schedule_autostop)