---
name: environment_issue
description: 确定性处理运行环境问题（WebSocket 连接失败、认证过期等）。环境问题无法通过修改 scenarios.json 解决，直接标记终止。
category: environment_issue
type: deterministic
trigger: AI 分类错误类型为 environment_issue 时自动触发
dependencies: []
confidence: 0.0
terminal: true
---

# EnvironmentIssueSkill

## 适用场景

当 AI 分析判断测试失败原因为 **运行环境问题** 时触发，包括：

- WebSocket 连接超时 / 拒绝连接
- 认证 token 过期（401/403）
- 服务不可达（ConnectionError）
- pytest 进程崩溃

## 修复策略

**确定性终止。** 环境问题无法通过修改测试数据或场景逻辑解决：

1. 记录 root_cause 到 history
2. 返回 `fix_action: "escalate_human"`
3. 不生成任何 fix_details
4. graph 路由到 END

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `root_cause` | analyze_failure | AI 给出的环境问题描述 |
| `error_category` | analyze_failure | 值为 "environment_issue" |

## 输出

- `fix_action`: `"escalate_human"`
- `fix_details`: `[]`
- `fix_proposal_confidence`: `0.0`
- `all_passed`: `False`
