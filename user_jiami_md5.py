import hashlib


def jiami():
    # 输入数据
    data = "AE11a5c73bd6ba8b939a17acad53caf85a2c"
    #data = "PeiTian_admin1"     # e2ab3ddd4ae58fd3b2320b418f96f7f5
    # data = "zx6900653"

    # 创建MD5对象
    md5_hash = hashlib.md5()

    # 更新MD5对象，将输入数据进行加密
    md5_hash.update(data.encode('utf-8'))

    # 获取32位小写MD5值
    md5_value = md5_hash.hexdigest()

    # 输出加密后的MD5值
    print(f"MD5 (32位小写): {md5_value}")

if __name__ == "__main__":
    jiami()