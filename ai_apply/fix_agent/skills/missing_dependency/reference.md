# upstream 依赖解析规则

本文件供 MissingDependencySkill 的确定性检查逻辑参考。

## semantics.json 中的依赖字段

```json
{
  "upstream": {
    "must_call_before": ["sim.loadModel"],
    "data_flow": [
      {"from_func": "sim.loadModel", "from_field": "ret[0]", "to_param_index": 0, "desc": "模型ID"}
    ],
    "system_state": "必须先加载模型"
  }
}
```

## 确定性修复逻辑

1. 遍历 `affected_interfaces`
2. 在 `semantics.json` 中找到对应接口的 `upstream.must_call_before`
3. 如果列表非空 → 缺少前置调用
4. 生成 `add_setup_step` fix_detail，reasoning 注明缺少的前置接口

## 示例

**失败**：`test_deleteModel_normal` 报错 "model not found"

**原因**：semantics 中 `sim.deleteModel` 的 `must_call_before: ["sim.loadModel"]`

**修复**：在 test_deleteModel 的 normal 场景中补充前置步骤 "需先调用 sim.loadModel"
