import requests
import pytest
from utils.conf_reader import load_config
from utils.logger import logger

"""账号生成器，按顺序提供可用账号"""
def get_available_accounts():
    config = load_config()

    # 直接从配置中获取账号列表
    # config['test_user'] 已经是一个包含多个账号字典的列表
    accounts = config["test_user"]

    for account in accounts:
        yield account  # 只要函数内部使用了 yield 关键字，这个函数就变成了一个 生成器函数


def get_token():
    """
    获取token的函数
    :return: (token, user_id) 元组
    """
    config = load_config()
    account_generator = get_available_accounts()
    success = False
    max_retries = 3  # 最大重试次数
    for attempt in range(max_retries):
        try:
            try:
                account = next(account_generator)
            except StopIteration:
                logger.warning("可用账号已耗尽，停止重试")
                break

            name = account["name"]
            password = account["password"]
            checkCode = account["checkCode"]

            logger.info(f"正在使用用户 {name} 进行登录！")
            login_payload = {
                "name": name,
                "password": password,
                "checkCode": checkCode
            }
            response = requests.post(config['gte_token_url'], json=login_payload)
            response_data = response.json()
            assert 'data' in response_data, "Response JSON is missing 'data' field"
            
            # 检查 data 是否为 None
            if response_data['data'] is None:
                # 如果 code 不是 200，说明登录失败，data 为空是正常的，应该让后面的 code 检查逻辑处理
                if response_data.get('code') != 200:
                    logger.error(f"Login failed for {login_payload['name']}. Response: {response_data}")
                    continue
                else:
                    # 如果 code 是 200 但 data 是 None，这是一个异常情况
                    pytest.fail(f"Login success (code 200) but data is None. Response: {response_data}")

            assert 'token' in response_data['data'], "Response JSON is missing 'token' field in 'data'"
            success = True
            break

        except requests.exceptions.RequestException as e:
            pytest.fail(f"Request failed with error: {e}")
        except AssertionError as e:
            pytest.fail(f"Assertion failed: {e}")
        except KeyError as e:
            pytest.fail(f"Missing expected key in response: {e}")
        except Exception as e:
            pytest.fail(f"Unexpected error: {e}")

    if not success:
        pytest.fail(f"无法获取Token，已尝试 {attempt + 1} 次")

    token = response_data['data']['token']
    # 尝试获取 userId，如果没有则默认 pt40 (或者根据实际响应字段修改，这里假设字段名为 userId)
    user_id = "pt" + str(response_data['data'].get('id'))

    return token, user_id


def get_headers(token):
    return {
        "Authorization": f"{token}"
    }


def logout(token):
    """
    退出登录
    :param token: 当前的 token
    """
    config = load_config()
    logout_url = config.get("logout_url")
    if not logout_url:
        logger.warning("配置文件中未找到 'logout_url'，跳过退出登录")
        return

    headers = get_headers(token)
    try:
        # 尝试 POST 请求退出
        response = requests.post(logout_url, headers=headers)
        if response.status_code == 200:
            logger.info("退出登录成功")
        else:
            logger.warning(f"退出登录失败: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"退出登录请求异常: {e}")