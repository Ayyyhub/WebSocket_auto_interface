import hashlib  # 确保导入hashlib模块


def md5_single(s: str) -> str:
    """单次MD5加密工具函数（32位小写）"""
    return hashlib.md5(s.encode('utf-8')).hexdigest()


def jiami():
    # 输入待加密数据
    data = input("请输入要加密的密码：")
    name = input("请输入被加密的账号：")

    # 第一次MD5加密
    first_md5 = md5_single(data)
    # 第二次MD5加密（对第一次加密结果再加密）
    second_md5 = md5_single(name+first_md5)

    # 输出过程与最终结果（方便调试）
    print(f"第一次MD5(32位小写)：{first_md5}")
    print(f"第二次MD5(32位小写)：{second_md5}")

    return second_md5


if __name__ == "__main__":
    # 执行两次加密并获取结果
    final_result = jiami()
    # 若仅需最终结果，可单独打印：
    # print(f"两次加密最终结果：{final_result}")