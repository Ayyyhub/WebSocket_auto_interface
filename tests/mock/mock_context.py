import threading

# 职责：测试级别控制
# 当前 test case 是 UNIT 还是 E2E
# 当前 test case 想测哪个接口
# 是否允许 mock / sandbox
#👉 这是“单元测试真正的开关”


class TestContextManager:
    """
    测试上下文管理器 (Thread-Local 单例)
    用于在 Unit Test 运行时，存储：
    1. 当前正在测试的目标接口 (target_func)
    2. 对特定接口的 Mock 行为覆盖 (mock_overrides)
    """
    # 1. 这是一个“全局变量”，用来存唯一的那个“管理员对象”
    _instance = None
    # 2. 这是一把“锁”,防止多个人（多线程）同时冲进来抢着当管理员
    _lock = threading.Lock()

    # 3. __new__ 是 Python 创建对象时第一个执行的方法,不管你调用多少次TestContextManager()，我都只给你同一个对象
    # 类方法 （Class Method）的第一个参数叫 cls ，代表 类对象本身 （人类这个概念模板）
    def __new__(cls):
        if not cls._instance:
            # 加上锁，确保这一刻只有我在操作
            with cls._lock:
                # 再检查一次（双重保险），如果确实还没管理员对象
                if not cls._instance:
                    # OK，创建一个新的对象，并把它任命为 _instance (唯一的管理员)
                    cls._instance = super(TestContextManager, cls).__new__(cls)
                    # 4. 给“管理员对象”( self ) 安装了一个属性，名字叫 local
                    # pytest并行,多case,不互相污染
                    cls._instance.local = threading.local()
        return cls._instance


    """当前被 @unittest_target 标记的接口名"""
    # @property 是 Python 的语法糖，让你能像访问变量一样访问函数
    @property
    def current_target(self):
        # getattr(对象, '属性名', 默认值)
        return getattr(self.local, 'target', None)

    @current_target.setter
    def current_target(self, value):
        self.local.target = value


    """当前测试用例定义的 Mock 覆盖规则"""
    @property
    def mock_overrides(self):
        if not hasattr(self.local, 'overrides'):
            self.local.overrides = {}
        return self.local.overrides

    """设置特定接口的 Mock 返回值"""
    def set_mock_override(self, func_name, response_data):
        self.mock_overrides[func_name] = response_data

    """获取特定接口的 Mock 返回值"""
    def get_mock_override(self, func_name):
        return self.mock_overrides.get(func_name)


    """清理上下文 (Teardown)"""
    def clear(self):
        self.local.target = None
        self.local.overrides = {}


# 全局单例
test_context = TestContextManager()
