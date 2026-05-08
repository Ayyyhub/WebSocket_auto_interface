"""
AI 自动生成的 WebSocket 工作流测试用例
场景: {{ scenario_name }}
生成时间: {{ generated_time }}

本测试按工作流顺序链式调用所有接口，
后续接口的参数从前面接口的返回值中提取。
"""

import pytest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from core.request_invoker import send_request


class Test{{ class_name }}:

    def test_workflow_happy_path(self, ws_client):
        """按工作流顺序执行所有接口，验证链式调用"""
        state = {}

{% for iface in interfaces %}
        # Step {{ iface.seq }}: {{ iface.func }}
{% if iface.args_detail %}
        resp_{{ iface.seq }} = send_request(
            ws_client,
            "{{ iface.func }}",
            {{ iface | build_workflow_args }},
            "{{ iface.desc }}",
        )
{% else %}
        resp_{{ iface.seq }} = send_request(
            ws_client,
            "{{ iface.func }}",
            [],
            "{{ iface.desc }}",
        )
{% endif %}
        assert resp_{{ iface.seq }} is not None, "Step {{ iface.seq }} {{ iface.func }} 返回为空"
        assert resp_{{ iface.seq }}.get("success") == True, f"Step {{ iface.seq }} {{ iface.func }} 失败: {resp_{{ iface.seq }}}"

{% if iface.response_usage %}
        if resp_{{ iface.seq }}.get("ret"):
            state["{{ iface.response_usage.captured_by }}"] = resp_{{ iface.seq }}["ret"][0]

{% endif %}
{% endfor %}
