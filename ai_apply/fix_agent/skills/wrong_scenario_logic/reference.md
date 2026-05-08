# category 与 should_success 对应规则

本文件供 WrongScenarioLogicSkill 的 AI prompt 参考使用。

## 标准对应关系

| category | should_success | 说明 |
|----------|---------------|------|
| `normal` | `true` | 正常场景应成功 |
| `boundary` | 视情况 | 合法边界值应为 true，越界值应为 false |
| `wrong_arg_type` | `false` | 错误类型参数应失败 |
| `missing_args` | `false` | 缺少必填参数应失败 |
| `violation` | `false` | 违反业务规则应失败 |
| `null_args` | 视情况 | 必填参数传 null 应 false，非必填可能 true |
| `invalid_func` | `false` | 不存在的 func 应失败 |

## 判断依据

1. **semantics.json 的 abnormal_responses**：定义了异常场景的预期响应
2. **semantics.json 的 business_rules**：定义了业务约束规则
3. **expected_response.success**：接口成功时的响应结构
4. **expected_response.error**：接口失败时的错误信息

## 常见矛盾模式

- `category: "normal"` + `should_success: false` → **矛盾**，正常场景应该成功
- `category: "missing_args"` + `should_success: true` → **矛盾**，缺少参数不应该成功
- `category: "violation"` + `should_success: true` → **矛盾**，违反规则不应该成功
