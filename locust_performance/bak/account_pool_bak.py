# locust_performance/account_pool.py
import queue
import threading
from utils.conf_reader import load_config
from utils.logger import logger


class AccountPool:
    """
    线程安全的账号池管理器
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
        """初始化账号池"""
        if self._initialized:
            return
        
        self._account_queue = queue.Queue()
        self._used_accounts = {}  # 记录正在使用的账号 {user_id: account}
        self._lock = threading.Lock()
        self._initialized = True
        self._load_accounts()
    
    def _load_accounts(self):
        """从配置文件加载账号到队列"""
        try:
            config = load_config()
            accounts = config.get("test_user", [])
            
            if not accounts:
                logger.warning("配置文件中未找到 test_user，账号池为空")
                return
            
            # 将账号放入队列（可以放入多次以实现循环使用）
            # 如果账号数量少于并发用户数，可以循环放入
            for account in accounts:
                self._account_queue.put(account)
            
            logger.info(f"账号池初始化完成，共加载 {len(accounts)} 个账号")
        except Exception as e:
            logger.error(f"加载账号失败: {e}")
            raise
    
    def get_account(self, timeout=5):
        """
        从账号池获取一个账号
        :param timeout: 超时时间（秒）
        :return: account dict 或 None
        """
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



# 为什么能解决多用户冲突？
# 问题场景（之前）
# 用户1调用 get_token() → 创建新生成器 → 获取账号A用户2调用 get_token() → 创建新生成器 → 获取账号A  ❌ 冲突！用户3调用 get_token() → 创建新生成器 → 获取账号A  ❌ 冲突！
# 解决方案（现在）
# 全局账号池（单例）├── 队列：[账号A, 账号B, 账号C, ...]│
# 用户1启动 → account_pool.get_account() → 获取账号A（从队列取出）
# 用户2启动 → account_pool.get_account() → 获取账号B（从队列取出）
# 用户3启动 → account_pool.get_account() → 获取账号C（从队列取出）
# 所有用户共享同一个账号池
# 队列的 get() 操作是线程安全的，保证每个账号只被一个用户获取