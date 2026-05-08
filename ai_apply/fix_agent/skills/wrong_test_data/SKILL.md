---
name: wrong_test_data
description: 确定性修复测试参数值不合理导致的失败。根据语义约束（valid_range、enum_values、boundary_values）重新计算参数值，不调用 AI。
category: wrong_test_data
type: deterministic
trigger: AI 分类错误类型为 wrong_test_data 时自动触发
dependencies:
  - data_builder.TestDataBuilder
confidence: 1.0
---

# WrongTestDataSkill

## 适用场景

当 AI 分析判断测试失败原因为 **参数值不合理** 时触发，包括：

- normal 场景中参数值不在合法范围或枚举值内
- boundary 场景中边界值不符合 valid_range
- wrong_arg_type / null_args 场景中类型与约束不匹配
- violation 场景中参数违反了业务规则约束

## 修复策略

**纯确定性，不调用 AI。** 直接复用 `TestDataBuilder._build_args()` 方法，根据语义约束重新计算每个场景的正确参数值：

1. 从 `semantics.json` 读取参数约束（type、valid_range、enum_values、boundary_values）
2. 根据场景 category 调用对应的构建方法（normal → 枚举首值/范围中值，boundary → 边界值，etc.）
3. 对比新旧 args，生成 fix_details

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `semantics` | load_artifacts 加载 | 参数约束定义 |
| `scenarios` | load_artifacts 加载 | 当前测试场景数据 |
| `affected_interfaces` | analyze_failure 产出 | 受影响的接口列表 |
| `failed_tests` | parse_pytest_output 产出 | 失败用例详情 |

## 输出

- `fix_action`: `"modify_args"`
- `fix_details`: 参数修改列表
- `fix_proposal_confidence`: `1.0`（确定性，无 AI 不确定性）

## 关联文件

- `reference.md` — 参数约束与 TestDataBuilder 映射关系
