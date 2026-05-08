---
name: uncertain
description: AI 辅助兜底 skill，处理无法确定分类的测试失败。复用原 propose_fix 的通用修复逻辑。
category: uncertain
type: ai_assisted
trigger: AI 分类错误类型为 uncertain，或其他 skill 未注册时的回退
dependencies:
  - ai_client.AIClient
  - schemas.FIX_PROPOSAL_TOOL
ai_model: gpt-4o
confidence_range: 0.1-0.5
---

# UncertainSkill

## 适用场景

当 AI 无法确定测试失败的明确分类时触发，作为兜底 skill：

- error_category 为 "uncertain"
- 注册表中找不到对应 category 的 skill 时自动回退

## 修复策略

**AI 辅助，通用修复。** 向 AI 提供完整的上下文信息，让它尝试提出修复方案：

1. 向 AI 提供：错误信息 + 场景数据 + 语义约束 + 历史修复记录
2. AI 尝试生成修复方案
3. 如果 AI 也无法修复，返回 `escalate_human`

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `root_cause` | analyze_failure | AI 给出的根因（可能不确定） |
| `failed_tests` | parse_pytest_output | 失败用例详情 |
| `scenarios` | load_artifacts | 完整场景数据 |
| `semantics` | load_artifacts | 完整语义约束 |
| `history` | 之前的节点 | 历史修复记录（避免重复策略） |

## 输出

- `fix_action`: AI 决定
- `fix_details`: AI 生成
- `fix_proposal_confidence`: 通常较低（0.1-0.5）
