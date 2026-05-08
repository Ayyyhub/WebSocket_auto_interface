---
name: missing_dependency
description: 混合修复前置接口未调用导致的失败。先查语义约束确定性补前置步骤，查不到再 AI 分析。
category: missing_dependency
type: hybrid
trigger: AI 分类错误类型为 missing_dependency 时自动触发
dependencies:
  - ai_client.AIClient
  - schemas.FIX_PROPOSAL_TOOL
confidence_range: 0.5-0.95
---

# MissingDependencySkill

## 适用场景

当 AI 分析判断测试失败原因为 **缺少前置接口调用** 时触发，包括：

- 测试 deleteModel 但没有先 loadModel
- 测试依赖上游接口返回的数据，但上游接口未调用
- 系统状态不满足（如未初始化就执行操作）

## 修复策略

**混合模式：先确定性，后 AI。**

### Phase 1：确定性检查
1. 从 `semantics.json` 读取 `upstream.must_call_before`
2. 如果能找到明确的前置依赖，直接生成 `add_setup_step` 修复方案
3. 置信度 0.9+，不需要 AI

### Phase 2：AI 回退
1. 如果语义中没有明确的前置依赖信息
2. 调用 AI 分析 upstream data_flow 关系，生成修复方案

## 输入

| 字段 | 来源 | 说明 |
|------|------|------|
| `semantics` | load_artifacts | 含 upstream.must_call_before、data_flow |
| `scenarios` | load_artifacts | 当前场景数据 |
| `affected_interfaces` | analyze_failure | 受影响接口 |
| `failed_tests` | parse_pytest_output | 失败用例详情 |

## 输出

- `fix_action`: `"add_setup_step"` 或 AI 给出的其他 action
- `fix_details`: 前置步骤修改列表
- `fix_proposal_confidence`: 确定性 0.9+，AI 回退 0.5+

## 关联文件

- `reference.md` — upstream 依赖解析规则
