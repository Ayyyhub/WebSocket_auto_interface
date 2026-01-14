# locustfile.py
# 一个用户就是一个实例==协程
from locust import task, between
from core.harness import send_request
from locust_performance.request_recorder import record_request
from locust_performance.users import BaseRobotUser
from locust_performance.scenarios import load_model_flow, full_teaching_flow, load_model
import locust_performance.response_time_monitor  # P1: 响应时间监控
import locust_performance.error_recorder  # P1: 错误详情记录
import locust_performance.scenarios_stats  # P1: 场景级统计
import locust_performance.runtime_customed  # P2: UI压测持续时间功能

class ComplexTask(BaseRobotUser):
    """
    压测场景 0：复杂场景
    """
    wait_time = between(1, 3)

    @task(5)
    def load_model_flow_task(self):
        """任务：加载模型流程"""
       
        record_request(self, "loadModel 加载模型链路", load_model_flow, self)
    @task(1)
    def full_teaching_task(self):
        """任务：完整示教流程"""
        record_request(self,"full_teaching_flow 完整示教流程", full_teaching_flow,self)
    @task(3)
    # self 是 QuickInterfaceTask 的实例，它继承自 BaseRobotUser
    # self 都代表是当前这个用户实例（QuickInterfaceTask → BaseRobotUser）
    def load_model_task(self):
        """任务：加载模型单接口"""
        # load_model(self)
        # 必须这样写，UI 才能看到数据，调用 load_model 函数，并上报到 monitors.py 里
        # self.record_request("loadModel 加载模型", load_model, self)
        record_request(self, "loadModel 加载模型单接口", load_model, self)



class LoadModelTask(BaseRobotUser):
    """
    压测场景 1：专门压加载模型链路
    """
    wait_time = between(1, 3)

    @task(5)
    def load_model_flow_task(self):
        """任务：加载模型流程"""
       
        record_request(self, "loadModel 加载模型链路", load_model_flow, self)



class FullTeachingTask(BaseRobotUser):
    """
    压测场景 2：完整示教流程
    """
    wait_time = between(1, 3)

    @task(1)
    def full_teaching_task(self):
        """任务：完整示教流程"""
        record_request(self,"full_teaching_flow 完整示教流程", full_teaching_flow,self)


class QuickInterfaceTask(BaseRobotUser):
    """
    压测场景 3：单接口压测
    """
    # 每个task间隔时间，1-3秒
    wait_time = between(1, 3)

    @task(3)
    # self 是 QuickInterfaceTask 的实例，它继承自 BaseRobotUser
    # self 都代表是当前这个用户实例（QuickInterfaceTask → BaseRobotUser）
    def load_model_task(self):
        """任务：加载模型单接口"""
        # load_model(self)
        # 必须这样写，UI 才能看到数据，调用 load_model 函数，并上报到 monitors.py 里
        # self.record_request("loadModel 加载模型", load_model, self)
        record_request(self, "loadModel 加载模型单接口", load_model, self)


"""
# 1. Locust 入口：locustfile.py
# Locust 根据配置启动 N 个用户。
# 对于每个用户，Locust 会创建一个 QuickInterfaceTask 实例，例如：
# 用户1 → 实例A（self_A）
# 用户2 → 实例B（self_B）
# 对每个实例，Locust 会自动调用：
# self.on_start()（继承自 BaseRobotUser）
# 然后按权重循环调用 load_model_task(self) 这个方法。
# 2. 用户启动：BaseRobotUser.on_start
# 在on_start()方法中，这里的 self 就是 QuickInterfaceTask 的实例（因为它继承了 BaseRobotUser）。
# on_start 里给这个实例挂了一些属性：
# self.user_id
# self.account
# self.ws_client ← WebSocket 客户端对象
# 所以之后只要手里有这个实例，就能访问对应的连接：实例.ws_client
# 3. Locust 调用任务方法：self 是当前这个用户实例（QuickInterfaceTask → BaseRobotUser）。

"""
