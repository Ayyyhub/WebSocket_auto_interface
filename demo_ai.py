"""
AI 生成式接口自动化测试 - 登录接口 Demo
接口: POST /rlrob/rest/signIn/default
请求体: {"checkCode": "string", "name": "string", "password": "string"}
响应体: {"code": int, "data": object, "message": string}
"""

import requests
import pytest


BASE_URL = "http://10.20.220.251/rlrob/rest"

# 测试账号（MD5加密后的密码）
VALID_ACCOUNT = {
    "name": "AE1",
    "password": "e2ab3ddd4ae58fd3b2320b418f96f7f5",
    "checkCode": "3d6a3e94beb8fd038b91716e0f55acf5"
}


class TestLogin:

    # ==================== 正常场景 ====================

    def test_login_success(self):
        """正常登录 - 使用合法账号密码"""
        payload = {
            "name": VALID_ACCOUNT["name"],
            "password": VALID_ACCOUNT["password"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert resp.status_code == 200
        assert data["code"] == 200, f"登录失败: {data.get('message')}"
        assert data["data"] is not None, "登录成功但 data 为空"
        assert "token" in data["data"], "响应中缺少 token 字段"

    # ==================== 异常场景 - 参数缺失 ====================

    def test_login_without_name(self):
        """缺少用户名"""
        payload = {
            "password": VALID_ACCOUNT["password"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, f"缺少name时应登录失败，实际code={data['code']}"

    def test_login_without_password(self):
        """缺少密码"""
        payload = {
            "name": VALID_ACCOUNT["name"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, f"缺少password时应登录失败，实际code={data['code']}"

    def test_login_empty_body(self):
        """空请求体"""
        resp = requests.post(f"{BASE_URL}/signIn/default", json={})
        data = resp.json()

        assert data["code"] != 200, f"空body时应登录失败，实际code={data['code']}"

    # ==================== 异常场景 - 错误凭证 ====================

    def test_login_wrong_password(self):
        """错误密码"""
        payload = {
            "name": VALID_ACCOUNT["name"],
            "password": "wrong_password_hash",
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "错误密码时应登录失败"

    def test_login_nonexistent_user(self):
        """不存在的用户"""
        payload = {
            "name": "nonexistent_user_999",
            "password": "some_hash",
            "checkCode": "some_code"
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "不存在的用户应登录失败"

    # ==================== 边界值场景 ====================

    def test_login_name_too_long(self):
        """用户名超长"""
        payload = {
            "name": "a" * 10000,
            "password": VALID_ACCOUNT["password"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "超长用户名应登录失败"

    def test_login_empty_name(self):
        """用户名为空字符串"""
        payload = {
            "name": "",
            "password": VALID_ACCOUNT["password"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "空用户名应登录失败"

    # ==================== 安全测试场景 ====================

    def test_login_sql_injection(self):
        """SQL注入测试"""
        payload = {
            "name": "' OR 1=1 --",
            "password": "' OR '1'='1",
            "checkCode": "anything"
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "SQL注入不应登录成功"

    def test_login_xss_injection(self):
        """XSS注入测试"""
        payload = {
            "name": "<script>alert(1)</script>",
            "password": VALID_ACCOUNT["password"],
            "checkCode": VALID_ACCOUNT["checkCode"]
        }
        resp = requests.post(f"{BASE_URL}/signIn/default", json=payload)
        data = resp.json()

        assert data["code"] != 200, "XSS注入不应登录成功"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
