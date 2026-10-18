import bcrypt


def hash_password(password: str) -> str:
    """
    哈希加密
    1. 把明文密码转 bytes
    2. gensalt() 自动生成随机盐
    3. hashpw 计算哈希
    4. decode 转回字符串存入数据库
    :param password: 前端明文密码
    :return: 哈希加盐后的字符串
    """
    # 1. 把明文密码转 bytes
    # 2. gensalt() 自动生成随机盐
    # 3. hashpw 计算哈希
    # 4. decode 转回字符串存入数据库
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    """
    #
    :param password: 前端明文密码
    :param hashed_password: 哈希加盐后的字符串
    :return: 返回 bool 值
    """
    return bcrypt.checkpw(
        password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )
