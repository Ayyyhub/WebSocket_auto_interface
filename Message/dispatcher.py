import json
import threading
import time
from utils.logger import logger

"""当从 WebSocket 收到的消息不是 JSON 格式时抛出"""
class NonJsonMessageError(Exception):
    def __init__(self, raw_message: str):
        super().__init__("收到非json响应")
        self.raw_message = raw_message


"""等待响应时，连续多次收到空消息（None），超过重试上限后抛出"""
class ResponseTimeoutError(Exception):
    def __init__(self, none_count: int):
        super().__init__(f"连续{none_count}次无响应")
        self.none_count = none_count


"""
    消息层：从连接层线程安全队列消费消息，统一做握手/系统消息过滤与JSON解析，
    并根据 id 进行分发缓存，确保业务层只拿到解析后的业务响应对象。
"""
class MessageDispatcher:
    def __init__(self, ws_client):
        self.ws_client = ws_client
        self._pending = {}
        self._lock = threading.Lock()

    # 给缓存加 “过期清理”（避免消息堆积）
    def _gc_pending(self, ttl=60):
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._pending.items() if isinstance(v, tuple) and now - v[1] > ttl]
            for k in expired:
                self._pending.pop(k, None)

    # _pop_pending适配 “元组格式的缓存”, 因为_cache_pending现在存的是元组，所以取缓存时要提取元组里的 “消息内容”：
    def _pop_pending(self, req_id: str):
        with self._lock:
            val = self._pending.pop(req_id, None)
        if val is None:
            return None
        if isinstance(val, tuple):
            return val[0]
        return val

    def _cache_pending(self, req_id: str, message):
        with self._lock:
            self._pending[req_id] = (message, time.time())

    # 手动清理所有缓存（例如在测试用例开始前调用，防止上一条用例的残留消息干扰）
    def clear_pending(self):
        with self._lock:
            self._pending.clear()
            logger.info("已清空 MessageDispatcher 的待决消息缓存")

    # 消息的过滤
    def _parse_raw(self, raw: str, desc: str):
        # logger.info(f"{desc} 原始消息: {raw}")
        try:
            parsed = json.loads(raw)
        except Exception:
            raise NonJsonMessageError(raw)

        if isinstance(parsed, dict):
            if parsed.get("message") == "ptcloud_pod_connect_success":
                logger.info(f"{desc} 云端Pod连接成功: {raw}")
                return None
            if parsed.get("func") == "simArcs.testPingPong" or parsed.get("id") == "ping":
                logger.info(f"{desc} 跳过心跳消息: {raw}")
        return parsed

    """
        阻塞等待匹配 req_id 的业务响应。
        - 过滤握手与系统消息
        - 非本次 id 的消息缓存起来
    """
    def wait_for_response(self, req_id: str, desc: str, max_none_retry: int = 3, timeout_per_recv: int = 5):
        none_count = 0
        start = time.time()

        while True:
            self._gc_pending()
            cached = self._pop_pending(req_id)
            if cached is not None:
                return cached, none_count, time.time() - start

            raw = self.ws_client.recv(timeout=timeout_per_recv)
            if raw is None:
                none_count += 1
                if none_count >= max_none_retry:
                    raise ResponseTimeoutError(none_count)
                logger.info(f"{desc}收到None，重试({none_count}/{max_none_retry})...")
                continue

            parsed = self._parse_raw(raw, desc)
            if parsed is None:
                # 握手或系统消息已在解析阶段过滤
                continue

            # 若消息 id 与当前 req_id 相同，返回作为本次响应
            msg_id = str(parsed.get("id")) if isinstance(parsed, dict) and "id" in parsed else None
            if msg_id and msg_id == req_id:
                return parsed, none_count, time.time() - start

            # 若不同 id ，缓存到待决表，供该请求未来消费
            if msg_id:
                self._cache_pending(msg_id, parsed)
                logger.info(f"{desc} 收到其他请求的响应(id={msg_id})，已缓存等待被消费")
                continue

            logger.info(f"{desc} 收到无id系统消息: {parsed}，继续等待真实响应")

