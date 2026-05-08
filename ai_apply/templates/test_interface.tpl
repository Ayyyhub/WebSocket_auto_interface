"""
AI 自动生成的接口测试用例
接口: {{ api }}
方法: {{ method }}
生成时间: {{ generated_time }}
"""

import pytest
import requests

BASE_URL = "{{ base_url }}"
{% if auth_token %}

# 鉴权 token（从登录接口获取）
AUTH_TOKEN = "{{ auth_token }}"
{% endif %}


class Test{{ class_name }}:

{% for scenario in scenarios %}
    def test_{{ scenario.name }}(self):
        """{{ scenario.description }}"""
        payload = {{ scenario.request_data | to_pretty_json }}
{% if auth_token %}
        headers = {"Authorization": AUTH_TOKEN}
        resp = requests.{{ method.lower() }}(f"{BASE_URL}{{ api }}", json=payload, headers=headers)
{% else %}
        resp = requests.{{ method.lower() }}(f"{BASE_URL}{{ api }}", json=payload)
{% endif %}
        data = resp.json()

        # {{ scenario.category }} 场景
{% for assertion in scenario.expected.assertions %}
        # {{ assertion }}
{% endfor %}
        assert resp.status_code == {{ scenario.expected.status_code }}
{% if scenario.category == "normal" %}
        assert data.get("code") == 200, f"{{ scenario.description }}失败: {data.get('message', '')}"
{% else %}
        assert data.get("code") != 200, "异常场景不应返回成功"
{% endif %}

{% endfor %}

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
