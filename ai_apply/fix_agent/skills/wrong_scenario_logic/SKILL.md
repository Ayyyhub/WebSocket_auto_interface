---
name: wrong_scenario_logic
description: AI 辅助修复测试场景预期结果矛盾（如异常场景期望 success=True，正常场景期望 success=False）。
category: wrong_scenario_logic
type: ai_assisted
trigger: AI 分类错误类型为 wrong_scenario_logic 时自动触发
dependencies:
  - ai_client.AIClient
  - schemas.FIX_PROPOSAL_TOOL
ai_model: gpt-4o
confidence_range: 0.5-0.9
---

# WrongScenarioLogicSkill

## 适用场景

当 AI 分析判断测试失败原因为 **预期结果写反** 时触发，包括：

- normal 场景期望 `success=False`（应该成功却预期失败）
- 异常场景（wrong_arg_type / missing_args / violation）期望 `success=True`（应该失败却预期成功）
- assertions 内容与接口实际响应不匹配

## 修复策略

**AI 辅助。** 使用 focused prompt 让 AI 判断 category 与 expected.should_success 是否矛盾：

1. 向 AI 提供：失败用例信息 + 场景的 category 与 should_success 对照 + 语义分析中的 abnormal_responses 和 business_rules
2. AI 判断哪些场景的预期需要修正
3. 生成修改 expected.should_success 或 expected.assertions 的 fix_details

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `failed_tests` | parse_pytest_output | 失败用例详情 |
| `scenarios` | load_artifacts | 当前场景数据 |
| `semantics` | load_artifacts | 含 abnormal_responses、business_rules |
| `root_cause` | analyze_failure | 根因分析文本 |

## 输出

- `fix_action`: 通常为 `"modify_expected"`
- `fix_details`: 预期结果修改列表
- `fix_proposal_confidence`: AI 给出，通常 0.5-0.9

## 关联文件

- `reference.md` — category 与 should_success 对应规则
