# locust_performance/account_pool.py

# 优化前
# conf.yaml: 100 个账号Locust: 启动 10 个用户→ 账号池加载 100 个账号（浪费 90 个）
# 优化后
# conf.yaml: 100 个账号Locust: 启动 10 个用户-> 账号池只加载 10 个账号

import queue
import threading
from utils.conf_reader import load_config
from utils.logger import logger


class AccountPool:
    """
    线程安全的账号池管理器（优化版：按需加载）
    用于 Locust 压测场景下的多用户账号分配
    """
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """单例模式，确保全局只有一个账号池实例"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(AccountPool, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """初始化账号池（延迟加载）"""
        if self._initialized:
            return
        
        self._account_queue = queue.Queue()
        self._used_accounts = {}  # 记录正在使用的账号 {user_id: account}
        self._lock = threading.Lock()
        self._all_accounts = None  # 存储所有可用账号（延迟加载）
        self._loaded_count = 0  # 已加载的账号数量
        self._initialized = True
        # 不再在这里加载账号，改为延迟加载
    
    def _ensure_accounts_loaded(self, target_user_count):
        """
        确保账号池中有足够的账号
        :param target_user_count: 目标用户数
        """
        with self._lock:
            # 如果账号列表未加载，先加载
            if self._all_accounts is None:
                try:
                    config = load_config()
                    self._all_accounts = config.get("test_user", [])
                    if not self._all_accounts:
                        logger.warning("配置文件中未找到 test_user，账号池为空")
                        return
                    logger.info(f"从配置文件加载了 {len(self._all_accounts)} 个账号")
                except Exception as e:
                    logger.error(f"加载账号失败: {e}")
                    raise
            
            # 计算需要加载的账号数量
            available_count = len(self._all_accounts)
            needed_count = min(target_user_count, available_count)
            
            # 如果当前队列中的账号数不足，补充账号
            current_queue_size = self._account_queue.qsize()
            if current_queue_size < needed_count:
                # 计算需要补充的数量
                to_add = needed_count - current_queue_size
                
                # 从账号列表中取对应数量的账号放入队列
                start_idx = self._loaded_count
                end_idx = min(start_idx + to_add, available_count)
                
                for i in range(start_idx, end_idx):
                    self._account_queue.put(self._all_accounts[i])
                
                self._loaded_count = end_idx
                logger.info(f"账号池已加载 {self._loaded_count} 个账号（目标用户数: {target_user_count}）")
    
    def get_account(self, target_user_count=None, timeout=5):
        """
        从账号池获取一个账号
        :param target_user_count: 目标用户数（用于按需加载）
        :param timeout: 超时时间（秒）
        :return: account dict 或 None
        """
        # 如果提供了目标用户数，确保有足够的账号
        if target_user_count is not None:
            self._ensure_accounts_loaded(target_user_count)
        
        try:
            account = self._account_queue.get(timeout=timeout)
            return account
        except queue.Empty:
            logger.warning("账号池为空，无法获取账号")
            return None
    
    def return_account(self, account):
        """
        归还账号到池中（可选，如果账号可以重复使用）
        :param account: 要归还的账号
        """
        if account:
            self._account_queue.put(account)
    
    def mark_account_in_use(self, user_id, account):
        """标记账号正在被使用"""
        with self._lock:
            self._used_accounts[user_id] = account
    
    def release_account(self, user_id):
        """释放账号"""
        with self._lock:
            account = self._used_accounts.pop(user_id, None)
            if account:
                # 可以选择归还账号或直接丢弃
                # self.return_account(account)  # 如果需要账号复用，取消注释
                pass


# 全局账号池实例
account_pool = AccountPool()




