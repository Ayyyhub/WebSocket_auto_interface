import sys
import time


def record_request(user_instance, name, func, *args, **kwargs):
        """
        一个通用的包装器，用来自动上报统计数据
        
        :param user_instance: Locust 用户实例（BaseRobotUser 或其子类）
        :param name: 请求名称（用于统计显示）
        :param func: 要执行的业务函数
        :param args: 传递给 func 的位置参数
        :param kwargs: 传递给 func 的关键字参数
        :return: func 的返回值
        """
        start_time = time.perf_counter()
        try:
            # func函数可以是 scenarios.py 里的业务函数，也可以是其他地方的函数
            # record_request(self, "loadModel 加载模型", load_model, self)最后一个self参数（实例）被 *args 接受
            result = func(*args, **kwargs)
            total_time = (time.perf_counter() - start_time) * 1000
            
            # events.request.fire() 会触发所有注册的 @events.request.add_listener 监听器 (例 monitors.py)
            user_instance.environment.events.request.fire(
                request_type="WS", name=name,
                response_time=total_time, response_length=0
            )
            return result
        
        except Exception as e:
            total_time = (time.perf_counter() - start_time) * 1000
            user_instance.environment.events.request.fire(
                request_type="WS", name=name,
                response_time=total_time, response_length=0, exception=e
            )
            raise e
        
        finally:
            sys.stdout.flush()


"""
# WebSocket 请求流程：
# 1. scenarios.py 调用业务函数
# 2. 业务函数通过 record_request 包装
# 3. record_request 执行函数并计时
# 4. record_request 调用 events.request.fire() 上报
#    ↓
# 5. @events.request.add_listener 监听器被触发 ✅
# 6. 监听器可以获取到：
#    - name: "加载模型接口"
#    - response_time: 1777.86ms
#    - exception: None 或异常对象
#    - ...
"""
