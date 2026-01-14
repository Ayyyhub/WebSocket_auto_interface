# web ui启动命令：
#  locust -f locust_performance/locustfile.py --host=http://dummy-host --web-port 8090
#  locust -f locust_performance/locustfile.py --host=http://dummy-host --web-port 8090 QuickInterfaceTask
# 无头模式启动命令
# locust -f locust_performance/locustfile.py \
#   --host=http://dummy-host \
#   --web-port 8090 \
#   --headless \
#   --users 50 \
#   --spawn-rate 5 \
#   --run-time 5m



"""
#   1、 使用线程安全的账号池，确保每个并发用户获取不同账号，避免冲突-->延迟加载 + 动态调整:不在模块导入时加载账号，而是在第一个用户启动时加载（只加载用户数对应的账号数量）。
#   2、 协程并发（单进程、多 greenlet），加gavent+Semaphore锁+非阻塞方式控制共享变量。（每个 Locust 虚拟用户（User 实例），本质上就是一个运行在 gevent 事件循环里的greenlet实例。）

"""



