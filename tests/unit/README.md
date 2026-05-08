###
---

# 1、parametrize：生成测试数据，只是声明
@pytest.mark.parametrize(
    "do_start,do_enable,do_switch,do_push,expect_success",  # ← 声明变量名
    [   
        (False, True,  True,  True,  True),   # ← 第 1 组数据
        (True,  False, True,  True,  True),   # ← 第 2 组数据
        ...
    ]
)

# 2、fixture：提供可调用工厂函数
@pytest.fixture
def jog_context_builder(ws_client):
    def build(do_start=True, do_enable=True, ...):  # ← 这里才是真正的参数定义
        # 根据参数执行逻辑
        ...
    return build

# 3、测试函数：接收双方注入的变量
def test_jog_preconditions(ws_client,        # ← fixture 注入
                           jog_context_builder, # ← fixture 注入
                           do_start,           # ← parametrize 注入（只是变量名）
                           do_enable,          # ← parametrize 注入（只是变量名）
                           ...):
    # 调用工厂函数，传入 parametrize 给的值
    client = jog_context_builder(
        do_start=do_start,      # 把 parametrize 的值传给工厂
        do_enable=do_enable,    # 把 parametrize 的值传给工厂
        ...
    )

---
