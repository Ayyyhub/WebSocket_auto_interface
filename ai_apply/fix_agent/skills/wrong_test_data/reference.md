# 参数约束与 TestDataBuilder 映射关系

本文件供 WrongTestDataSkill 参考取值逻辑。

## semantics.json 参数约束字段

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `type` | str | 参数数据类型 | `int`, `str`, `float`, `list` |
| `required` | int | 0=必填, 1=非必填 | `0` |
| `valid_range` | str | 合法范围 | `"0-5"`, `"-1000~1000"` |
| `enum_values` | list | 枚举值列表 | `["model_a", "model_b"]` |
| `boundary_values` | list | 边界值列表 | `["0", "-1", "6"]` |
| `special_char_limit` | str | 特殊字符限制 | `"不允许 < > &"` |

## TestDataBuilder._build_args 分类取值规则

### normal 场景
1. 有 enum_values → 取第一个枚举值
2. 有 valid_range → 取范围中值 `(min + max) // 2`
3. 都没有 → 取类型默认值（int→0, str→"", float→0.0, list→[]）

### boundary 场景
1. 先生成 normal 参数
2. 有 boundary_values → 用第一个边界值替换对应参数
3. 有 valid_range → 用 `min - 1` 作为边界值

### wrong_arg_type 场景
1. 先生成 normal 参数
2. 把第一个参数替换为错误类型值（int→"not_a_number", str→12345）

### missing_args 场景
1. 先生成 normal 参数
2. 删除第一个必填参数

### null_args 场景
1. 先生成 normal 参数
2. 把第一个非必填参数设为 None

### violation 场景
1. 先生成 normal 参数
2. int 类型 → 替换为 -999，str 类型 → 替换为 ""

### invalid_func 场景
1. 返回空列表 `[]`
