-优先掌握高频款：23 种中只需掌握 10 种左右就能覆盖 80% 场景 —— 
单例、工厂方法、建造者、代理、适配器、装饰器、门面、
策略、观察者、模板方法、责任链


-接口自动化：先掌握单例（会话）、工厂（多环境）、 策略（多断言）、装饰器（日志）、门面（业务封装）



### 核心角色
1. ws_client Fixture (conftest.py) :
   
   - 角色 ：工厂 / 创造者。
   - 职责 ：负责创建 WSClient 的 物理实例 ，负责插网线（connect）、拔网线（close）。
   - 生命周期 ：Session 级（生一次，死一次）。在内存中，它创造了一个真实的 Python 对象，假设地址是 0x1234 。
2. _dispatchers 字典 (core/ws_request.py) :
   
   - 角色 ：管家登记表。
   - 职责 ：负责管理“谁来处理 0x1234 这个连接的消息”。
   - 机制 ：Key 是 0x1234 (client ID)，Value 是 MessageDispatcher 实例。
3. ws_send_and_wait (core/ws_request.py) :
   
   - 角色 ：业务员。
   - 职责 ：拿着 ws_client 实例去办事。
### 数据流动全景图
第一阶段：初始化 (conftest.py)

1. Pytest 启动，发现需要 ws_client fixture。
2. WSClient 被实例化 (内存地址 0x100 )。
3. client.connect() 建立物理连接。
4. 关键时刻 ：您刚才添加的 ws_clear_pending(client) 被调用。
   - 它内部调用 _get_dispatcher(client) 。
   - _get_dispatcher 检查 _dispatchers 字典，发现 0x100 没注册。
   - 于是，它创建了第一个 MessageDispatcher (管家)，绑定给 0x100 。
   - 现在 _dispatchers = { 0x100: DispatcherA } 。
   - DispatcherA 被清空缓存。
5. yield client ：fixture 把这个 0x100 的实例交给了测试用例。
第二阶段：测试执行 (test_loadmodel.py)

1. 用例 A 开始，拿到了 client (还是那个 0x100 )。
2. 用例调用 ws_loadmodel_chain() -> 内部调用 ws_send_and_wait(..., ws_client=client) 。
3. ws_send_and_wait 拿到 client ( 0x100 )，去问 _dispatchers ：
   - "嘿， 0x100 的管家是谁？"
   - _dispatchers 查表：" 0x100 对应的管家是 DispatcherA 。" (就是刚才初始化时创建的那个！)
4. 结果 ：所有请求都通过 DispatcherA 发送和接收。如果请求 A 发出后，响应慢了，被缓存到了 DispatcherA 的 _pending 里，后续的逻辑依然能通过 DispatcherA 找回这个响应。
第三阶段：下一个测试用例

1. 用例 B 开始，Pytest 依然把同一个 client ( 0x100 ) 传给它 (因为是 Session scope)。
2. 用例 B 再次调用 ws_send_and_wait 。
3. 代码再次去查 _dispatchers 表，依然拿到 DispatcherA 。
4. 这就是为什么我们需要手动清理缓存 ：因为 DispatcherA 从头活到尾，如果用例 A 留了垃圾，用例 B 还能看见。
### 总结
- conftest 里的 ws_client 负责 物理连接的唯一性 （整个测试就这根网线）。
- _dispatchers 负责 逻辑处理的唯一性 （整个测试就这个管家在盯着这根网线）。
它们不仅不冲突，反而共同保证了“单例模式”在整个测试生命周期中的贯彻。 如果没有 _dispatchers 字典，每次 ws_send_and_wait 都 new 一个 Dispatcher，那之前的缓存就全都丢了，这才是真正的灾难。




项目亮点：
1、设计了一套基于单例注册表的异步消息分发系统，通过连接与分发器的强绑定，结合‘暂存-消费’机制，完美解决了 WebSocket 测试中高并发、响应乱序及丢包等核心难题，确保了测试用例的稳定性与数据的完整性。
2、通过「工厂模式夹具」与「参数化测试」两大特性的协同，实现单元测试批量覆盖