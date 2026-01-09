import queue
from socket import timeout
import socket
import websocket
import threading
import json
import time
from utils.logger import logger
socket.setdefaulttimeout(10)


""" 封装一个’连接层‘的可复用的 WebSocket 客户端类 """
# 连接层（Connection Layer）
# - 关注连接生命周期：建连、断连、重连、心跳保活、并发安全
# - 对事件回调的行为验证： on_open 、 on_message 、 on_error 、 on_close
# - 针对异常网络条件的健壮性：超时、半开连接、服务器关闭、TLS/认证错误

class WSClient:
    def __init__(self, ws_url, user_id, token):
        self.ws_url = f"{ws_url}?userId={user_id}&Authorization={token}"
        self.ws = None
        self.connected = False            # 状态位,判断连接是否成功的唯一信号灯
        self.queue = queue.Queue()

# WebSocket事件回调
    def on_message(self, ws, message): # --> 改为线程安全的队列，做到不覆盖，消息不丢失
        # with self._lock:
        #     self.last_message = message
        print("\n")
        logger.info(f"[WSClient] 收到原始数据: {message[:200]}..." if len(message) > 200 else f"[WSClient] 收到原始数据: {message}")
        self.queue.put_nowait(message)

    def on_error(self, ws, error):
        logger.error(f"WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        # print(f"WebSocket closed: {close_status_code} {close_msg}")
        self.connected = False

    def on_open(self, ws):          # 当子线程里的 run_forever 成功与服务器建立了连接，底层库会自动调用我们注册的 on_open 函数。
        # print("WebSocket connection opened.")
        self.connected = True


# 连接管理
    def connect(self):
        timeout = 30  # 定义超时时间为 30 秒
        self.ws = websocket.WebSocketApp(
            self.ws_url,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close,
            on_open=self.on_open
        )
        ping_interval = 3  # 每隔 3 秒发送一次心跳
        ping_timeout = 2  # 如果 3 秒内没有回应，就认为超时

        # 1. 给 run_forever 增加 ping 机制，防止死连接
        # run_forever启动客户端的事件循环并维持连接，直到显式关闭或发生错误
        # run_forever这是一个阻塞函数，它负责底层的 Socket 连接、握手、心跳维持和数据接收
        # ping_interval: 每隔多少秒发送一次心跳
        # ping_timeout: 心跳多久没回应算超时
        self.thread = threading.Thread(target=self.ws.run_forever, kwargs={
            "ping_interval": ping_interval,
            "ping_timeout": ping_timeout
        })

        self.thread.daemon = True   # 守护线程，主程序退出时它也会自动退出
        self.thread.start()         # <--- 真正开始干活，发起 TCP 连接和 WebSocket 握手
        
        # 2. 改进后的连接等待逻辑
        start_time = time.time()
        while not self.connected:
            if time.time() - start_time > timeout:
                self.close() # 超过时间没连上，强行关闭
                raise Exception(f"WebSocket 连接超时 (未能在 {timeout}s 内建立握手)")
            time.sleep(0.1) # 缩短轮询间隔，反应更快
        
        logger.info(f"WebSocket 连接成功，耗时: {time.time() - start_time:.2f}s")


# 消息发送
    def send(self, data):
        if not self.ws or not self.connected:
            # 这里的报错可以同步给 Locust 的统计
            raise Exception("WebSocket未连接，无法发送数据")
        
        if isinstance(data, dict):
            data = json.dumps(data)
            
        try:
            self.ws.send(data)
        except Exception as e:
            self.connected = False
            raise Exception(f"发送数据失败: {e}")


# 消息接收（从队列拉取）
    def recv(self, timeout=5):
        try:
            # 直接利用 queue 的超时功能，这是最稳妥的
            return self.queue.get(timeout=timeout)
        except queue.Empty:
            # logger.warning(f"接收消息超时 ({timeout}s)")
            return None


# 关闭
    def close(self):
        if self.ws:
            self.ws.close()


