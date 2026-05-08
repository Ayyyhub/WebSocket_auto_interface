### 一、
┌─────────────────────────────────────────────────────────────────┐
│                    AI 生成式接口自动化测试流程                     │
└─────────────────────────────────────────────────────────────────┘
Service 层代码（loadmodel_chain.py 等）
        │
        ▼
┌─ 第一步：轻量 AST 提取（确定性，无 AI）──────────────────────────┐
│  只做：按顺序提取 send_request 调用列表                           │
│  不做：状态追踪、依赖分析、子工作流检测                            │
│  产出 ① raw_interfaces.json                                      │
│  可独立验证：python workflow_parser.py loadmodel                  │
└─────────────────────────────────────────────────────────────────┘
        │ raw_interfaces.json
        ▼
┌─ 第二步：从钉钉文档获取接口完整定义（可选）─────────────────────────┐
│  DingTalkDocSkill → 按接口名去钉钉拉文档                          │
│  带 TTL 缓存，用 --refresh-docs 强制刷新                         │
│  获取失败 → 跳过，后续步骤用 raw_interfaces 补位                   │
│  产出 ② dingtalk_docs.json（可能为空）                            │
│  可独立验证：python dingtalk_skill.py loadmodel                  │
└─────────────────────────────────────────────────────────────────┘
        │ raw_interfaces.json + dingtalk_docs.json
        ▼
┌─ 第三步：workflow_ai_analyzer.py AI 对工作流关系分析（第 1 次 AI 调用）─┐
│  输入：raw_interfaces + 钉钉文档 + Service 层代码原文                 │
│  AI 分析：                                                         │
│    · 接口之间的调用顺序和依赖关系                                     │
│    · 数据流向（A 的返回值 → B 的参数）                               │
│    · 子工作流调用关系                                               │
│    · 状态变量的产出和消费链                                         │
│  产出 ③ workflow.json（关系图）                                     | 
│  可独立验证：python workflow_ai_analyzer.py loadmodel              │
│  出问题时：检查 prompt + 输入是否完整                                 │
└───────────────────────────────────────────────────────────────────┘
        │ workflow.json
        ▼
┌─ 第四步：semantic_parser.py AI 对每个接口进行语义分析（第 2 次 AI 调用）─────┐
│  输入：workflow.json + raw_interfaces + 钉钉文档                         │
│  AI 分析：                                                               │
│    · 每个接口的业务含义                                                   │
│    · 参数约束（类型、范围、枚举、必填）                                     │
│    · 预期响应结构                                                        │
│    · 查询型/操作型分类                                                    │
│  产出 ④ semantics.json                                                  │
│  可独立验证：python semantic_parser.py loadmodel                         │
│  出问题时：检查 workflow.json 是否正确                                     │
└─────────────────────────────────────────────────────────────────────────┘
        │ workflow.json + semantics.json
        ▼
┌─ 第五步：ai_generator.py AI 生成测试场景（第 3 次 AI 调用）──────────┐
│  输入：workflow.json + semantics.json                             │
│  AI 生成：normal / boundary / 异常 测试场景                        │
│  产出 ⑤ scenarios.json                                            │
│  可独立验证：python ai_generator.py loadmodel                     │
│  出问题时：回溯 semantics.json 是否合理                             │
└──────────────────────────────────────────────────────────────────┘
        │ scenarios.json
        ▼
┌─ 第六步：渲染 pytest 代码（确定性，无 AI）───────────────────────┐
│  Jinja2 模板 + scenarios.json → pytest 测试代码                   │
│  产出 ⑥ test_xxx.py                                               │
│  可独立验证：直接读生成的 .py 文件                                  │
└─────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─ 第七步：执行测试（可选，--execute）─────────────────────────────┐
│  pytest -v --tb=short                                              │
└─────────────────────────────────────────────────────────────────┘



### 二、
我的看法：现阶段不需要 skills，原因有三：

# 1. 你当前的瓶颈不是 AI 能力不够，是喂给 AI 的上下文不够

看 ai_generator.py 的 prompt，它只知道"每个接口的 func、args、desc"，不知道：

这个接口在工作流里排第几步
它的参数依赖哪个上游返回值
前置条件是什么
这不是 skills 能解决的，是prompt 缺少 workflow 上下文。你已经有 workflow.json 了，但没有喂进去。


# 2. Skills 解决的是 "AI 需要外部工具" 的问题，你现在不需要

Skills 的典型场景：

AI 需要查数据库 → 给它一个 query_tool
AI 需要跑代码验证 → 给它一个 code_runner
AI 需要多轮决策 → 给它 agent 循环
你现在的场景是：输入一段接口描述，输出一份测试场景 JSON。这是一个确定性的单轮映射，不需要外部工具。


# 3. 加 skills = 破坏你的架构原则

目前原则是"确定性 Pipeline + 单点 AI"。Skills 本质上是让 AI 拥有行动能力，等于从"单点"变成"多点"，pipeline 的确定性就没了。

真正该做的优先级：

优先级	    事项	                                                效果
P0	    把 workflow.json 的状态流喂进 ai_generator 的 prompt	AI 能理解接口依赖关系
P0	    修 workflow_parser 的两个缺陷	                        解析出完整的工作流图
P1	    做 workflow-aware 测试模板	                            生成的代码能跑通
P2	    多轮生成（先出场景，再出代码）	                            代码质量更高


# 4. 解释确定性 Pipeline + 单点 AI

用你现在的代码举例：

"单点 AI" — 你的 pipeline 里只有两个地方调 AI：


doc_parser(AST) → semantic_parser(AI) → ai_generator(AI) → code_renderer(Jinja2)
                   ↑ 唯一AI点1          ↑ 唯一AI点2          ↑ 确定性
每次 AI 调用都是输入确定、输出确定的：给一段接口描述，返回一份 JSON。AI 没有"行动能力"，它不能去查数据库、不能去跑代码、不能去调用别的接口。

"Skills"会变成什么样：


doc_parser(AST) → semantic_parser(AI+skill:查数据库) → ai_generator(AI+skill:跑测试验证) → ...
AI 突然能"做事"了——它可以自己决定要不要查数据库、要不要跑一遍测试看看对不对、要不要再调一次 API。这意味着：

每次跑的结果可能不一样 — AI 可能今天查了数据库，明天觉得不需要查
pipeline 不再是直线 — 变成了循环、分支，你无法预测执行路径
调试困难 — 出了问题你不知道是 AI 的哪次"自主决策"导致的

一句话总结：

单点 AI = AI 是工具，你喂什么它吐什么，pipeline 你完全可控
Skills = AI 变成智能体，它自己决定做什么，pipeline 你控制不了
你现在的场景不需要 AI 自主决策，你需要的是喂给它更完整的上下文（workflow.json 的依赖关系），让它吐出更准确的测试场景。这是 prompt 层面的事，不是 skills 层面的事。




