---
name: template_issue
description: AI 辅助修复渲染模板生成的代码问题（语法错误、import 缺失等）。
category: template_issue
type: ai_assisted
trigger: AI 分类错误类型为 template_issue 时自动触发
dependencies:
  - ai_client.AIClient
  - schemas.FIX_PROPOSAL_TOOL
ai_model: gpt-4o
confidence_range: 0.3-0.7
---

# TemplateIssueSkill

## 适用场景

当 AI 分析判断测试失败原因为 **模板渲染问题** 时触发，包括：

- 生成的 Python 代码有语法错误（SyntaxError）
- import 缺失（ImportError、NameError）
- 模板变量替换异常导致代码格式错误

## 修复策略

**AI 辅助。** 使用 focused prompt 让 AI 分析模板渲染问题：

1. 向 AI 提供：失败的 traceback（含 SyntaxError/ImportError）+ 相关场景数据
2. AI 判断是数据问题（特殊值导致模板渲染异常）还是模板 bug
3. 数据问题 → 生成修改 args 的 fix_details
4. 模板 bug → 返回 `escalate_human`

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `failed_tests` | parse_pytest_output | 含 traceback（SyntaxError/ImportError） |
| `scenarios` | load_artifacts | 相关场景数据 |
| `root_cause` | analyze_failure | 根因分析 |

## 输出

- `fix_action`: `"modify_args"` 或 `"escalate_human"`
- `fix_details`: 数据修改列表（如果可修复）
- `fix_proposal_confidence`: 通常较低（0.3-0.7）
