"""
AI 自动生成的 WebSocket 接口测试用例
场景: {{ scenario_name }}
生成时间: {{ generated_time }}
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from core.request_invoker import send_request


class Test{{ class_name }}:

{% set seen_names = [] %}
{% for iface in interfaces %}
    # ==================== {{ iface.func }} ====================
{% for scenario in iface.test_scenarios %}
{% set base_name = scenario.name %}
{% if base_name in seen_names %}
{% set method_name = base_name ~ "_" ~ iface.func.replace(".", "_") %}
{% else %}
{% set method_name = base_name %}
{% endif %}
{% do seen_names.append(base_name) %}
    def test_{{ method_name }}(self, ws_client):
        """{{ scenario.description }}"""
        resp = send_request(
            ws_client,
            "{{ iface.func }}",
            {{ scenario.args | to_pretty_json }},
            "{{ scenario.description }}"
        )
{% if scenario.expected.should_success %}
        assert resp is not None, "{{ scenario.description }} 返回为空"
        assert resp.get("success") == True, f"{{ scenario.description }} 失败: {resp}"
{% else %}
        # 异常场景：接口应返回 success=False 或抛出异常
        if resp is not None:
            assert resp.get("success") == False, "异常场景不应返回成功"
{% endif %}

{% endfor %}
{% endfor %}


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
