"""
工作流解析器 - 增强版

从 Service chain 文件中确定性提取完整的工作流信息：
- 按顺序提取 send_request 调用列表
- 追踪变量赋值和使用（状态变量追踪）
- 分析接口之间的依赖关系（upstream/downstream）
- 检测子工作流调用
- 识别控制流（try/except, sleep, 条件分支）

输出与原 workflow_ai_analyzer.py (LLM) 完全相同的 JSON 结构，
下游 semantic_parser / scenario_generator 无需修改。
"""

import ast
import json
import os
from typing import Optional

# Python 3.8 兼容：ast.unparse 在 3.9 才有
if hasattr(ast, "unparse"):
    _unparse = ast.unparse
else:
    def _unparse(node):
        """简易 ast.unparse 替代，覆盖 workflow_parser 中用到的 AST 节点类型"""
        if node is None:
            return ""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            if isinstance(node.value, str):
                return repr(node.value)
            return str(node.value)
        if isinstance(node, ast.Num):
            return str(node.n)
        if isinstance(node, ast.Str):
            return repr(node.s)
        if isinstance(node, ast.Attribute):
            return f"{_unparse(node.value)}.{node.attr}"
        if isinstance(node, ast.Subscript):
            return f"{_unparse(node.value)}[{_unparse(node.slice)}]"
        if isinstance(node, ast.Index):
            return _unparse(node.value)
        if isinstance(node, ast.Call):
            args = ", ".join(_unparse(a) for a in node.args)
            return f"{_unparse(node.func)}({args})"
        if isinstance(node, ast.Compare):
            left = _unparse(node.left)
            ops = {"Eq": "==", "NotEq": "!=", "Lt": "<", "LtE": "<=", "Gt": ">", "GtE": ">=", "Is": "is", "IsNot": "is not"}
            parts = [left]
            for op, comp in zip(node.ops, node.comparators):
                op_str = ops.get(type(op).__name__, "?")
                parts.append(f"{op_str} {_unparse(comp)}")
            return " ".join(parts)
        if isinstance(node, ast.BoolOp):
            op = " and " if isinstance(node.op, ast.And) else " or "
            return op.join(_unparse(v) for v in node.values)
        if isinstance(node, ast.UnaryOp):
            return f"{type(node.op).__name__} {_unparse(node.operand)}"
        if isinstance(node, ast.List):
            return "[" + ", ".join(_unparse(e) for e in node.elts) + "]"
        if isinstance(node, ast.Tuple):
            return "(" + ", ".join(_unparse(e) for e in node.elts) + ")"
        if isinstance(node, ast.keyword):
            return f"{node.arg}={_unparse(node.value)}"
        return f"<expr>"


# ==================== 公共 API ====================

def parse_workflow(file_path: str) -> dict:
    """
    解析单个 chain 文件，返回接口列表 + 源代码原文（轻量版，兼容旧接口）。
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    filename = os.path.basename(file_path)
    workflow_name = os.path.splitext(filename)[0]

    interfaces = []
    seq = 0
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not _is_send_request(node):
            continue
        if len(node.args) < 4:
            continue

        func_name = _extract_str(node.args[1])
        if not func_name:
            continue

        seq += 1
        interfaces.append({
            "seq": seq,
            "func": func_name,
            "args": _extract_args(node.args[2]),
            "desc": _extract_str(node.args[3]) or "",
        })

    return {
        "workflow_name": workflow_name,
        "source_file": filename,
        "source_code": source_code,
        "interfaces": interfaces,
    }


def parse_workflow_enhanced(file_path: str) -> dict:
    """
    解析单个 chain 文件，返回完整的工作流分析结果（增强版，替代 LLM）。

    输出结构：
    {
        "workflow_name": "loadmodel_chain",
        "source_file": "loadmodel_chain.py",
        "source_code": "完整源代码文本",
        "interfaces": [
            {"seq", "func", "desc", "call_type", "args_detail",
             "response_usage", "upstream", "downstream"}
        ],
        "state_flow": [
            {"var_name", "produced_by", "consumed_by", "extract_path"}
        ],
        "sub_workflows": [
            {"target_class", "target_method", "source_file", "passed_params"}
        ],
        "control_flow": {
            "has_try_except", "delays", "conditionals"
        }
    }
    """
    with open(file_path, "r", encoding="utf-8") as f:
        source_code = f.read()

    tree = ast.parse(source_code)
    filename = os.path.basename(file_path)
    workflow_name = os.path.splitext(filename)[0]

    # 找到 chain 方法的节点（类方法或独立函数）
    chain_body = _find_chain_body(tree)

    # 分析控制流
    control_flow = _analyze_control_flow(chain_body)

    # 按顺序遍历语句，追踪变量
    ctx = _WorkflowContext()
    _walk_statements(chain_body, ctx)

    # 构建状态流和 downstream（必须在遍历完成后调用）
    ctx.build_state_flow()

    # 构建最终输出
    return {
        "workflow_name": workflow_name,
        "summary": ctx.summary,
        "source_file": filename,
        "source_code": source_code,
        "interfaces": ctx.interfaces,
        "state_flow": ctx.state_flow,
        "sub_workflows": ctx.sub_workflows,
        "control_flow": control_flow,
    }


def merge_with_dingtalk_docs(workflow: dict, dingtalk_docs: Optional[dict]) -> dict:
    """
    将钉钉文档的接口详情合并到工作流中。

    按接口 func 名匹配，把钉钉文档中的 params、description 补充到对应接口。
    无钉钉文档的接口保持原始 AST 提取的信息。
    """
    if not dingtalk_docs:
        return workflow

    for iface in workflow.get("interfaces", []):
        func_name = iface.get("func", "")
        doc = dingtalk_docs.get(func_name)
        if not doc:
            continue

        # 补充参数定义
        if doc.get("params") and not iface.get("dingtalk_params"):
            iface["dingtalk_params"] = doc["params"]

        # 补充接口描述（钉钉文档的更详细）
        if doc.get("description") and not iface.get("dingtalk_description"):
            iface["dingtalk_description"] = doc["description"]

    return workflow


def format_for_ai(workflow: dict) -> str:
    """将接口列表格式化为 AI 可读文本"""
    lines = []
    lines.append(f"# 工作流: {workflow['workflow_name']}")
    lines.append(f"# 来源: {workflow.get('source_file', '')}")
    interfaces = workflow.get("interfaces", [])
    lines.append(f"# 接口数量: {len(interfaces)}")
    lines.append("")

    for iface in interfaces:
        args_str = json.dumps(iface.get("args", []), ensure_ascii=False)[:120]
        lines.append(f"### 接口 {iface.get('seq', '?')}: {iface.get('func', '?')}")
        lines.append(f"描述: {iface.get('desc', '')}")
        lines.append(f"参数: {args_str}")
        # 补充文档中的参数说明
        if iface.get("dingtalk_params"):
            lines.append("文档参数定义:")
            for p in iface["dingtalk_params"]:
                lines.append(f"  - {p.get('name', '?')}: {p.get('description', '')}")
        lines.append("")

    return "\n".join(lines)


def format_workflow_for_generator(workflow: dict) -> str:
    """将 workflow.json 格式化为文本，供后续 AI 步骤使用"""
    lines = []
    lines.append(f"# 工作流: {workflow.get('workflow_name', '')}")
    lines.append(f"# 概述: {workflow.get('summary', '')}")
    lines.append("")

    lines.append("## 接口调用顺序与依赖关系")
    lines.append("")
    for iface in workflow.get("interfaces", []):
        lines.append(f"### Step {iface['seq']}: {iface['func']}")
        lines.append(f"描述: {iface.get('desc', '')}")
        lines.append(f"调用类型: {iface.get('call_type', '')}")
        if iface.get("upstream"):
            lines.append(f"上游依赖: {', '.join(iface['upstream'])}")
        if iface.get("downstream"):
            lines.append(f"下游消费: {', '.join(iface['downstream'])}")
        ru = iface.get("response_usage") or {}
        if ru.get("captured_by"):
            lines.append(f"返回值: 捕获到 {ru['captured_by']}, 提取路径: {ru.get('extract_path', '')}")
            if ru.get("used_by"):
                lines.append(f"被下游使用: {', '.join(ru['used_by'])}")
        if iface.get("args_detail"):
            lines.append("参数详情:")
            for ad in iface["args_detail"]:
                lines.append(f"  args[{ad['index']}]: {ad.get('value', '?')} (来源: {ad.get('source', '?')})")
        lines.append("")

    if workflow.get("state_flow"):
        lines.append("## 状态变量流")
        lines.append("")
        for sf in workflow["state_flow"]:
            lines.append(f"- **{sf['var_name']}**: 产出={sf.get('produced_by', '?')}, 消费={sf.get('consumed_by', [])}")
        lines.append("")

    if workflow.get("sub_workflows"):
        lines.append("## 子工作流")
        lines.append("")
        for sw in workflow["sub_workflows"]:
            lines.append(f"- {sw['target_class']}.{sw.get('target_method', '?')} ({sw.get('source_file', '')})")
        lines.append("")

    return "\n".join(lines)


# ==================== 内部实现 ====================

class _WorkflowContext:
    """解析过程中的上下文状态"""

    def __init__(self):
        self.interfaces = []
        self.state_flow = []
        self.sub_workflows = []
        self.summary = ""

        self._seq = 0
        # 追踪：变量名/属性名 → 产出信息
        self._var_producers = {}   # "变量名" → {"func": "sim.loadModel", "seq": 1, "extract_path": "..."}
        self._attr_producers = {}  # "Class.attr" → {"func": "...", "seq": 1, "extract_path": "..."}
        # 当前活跃的响应变量
        self._response_vars = {}   # "resp_var_name" → {"seq": 1, "func": "sim.loadModel"}

    @property
    def seq(self):
        self._seq += 1
        return self._seq

    def record_response_capture(self, var_name: str, seq: int, func: str):
        """记录响应被变量捕获"""
        self._response_vars[var_name] = {"seq": seq, "func": func}

    def record_state_production(self, var_key: str, extract_path: str):
        """记录状态变量被产出（从响应中提取值赋给变量/属性）"""
        source = self._response_vars.get(var_key.rsplit(".", 1)[-1] if "." not in var_key else None)

        # 尝试通过变量名找到对应的响应变量
        # 对于 Class.attr = resp["ret"][0]，var_key 是 resp 变量名
        resp_info = self._response_vars.get(var_key)
        if not resp_info:
            return

        self._var_producers[var_key] = {
            "func": resp_info["func"],
            "seq": resp_info["seq"],
            "extract_path": extract_path,
        }

    def record_attr_production(self, attr_key: str, resp_var_name: str, extract_path: str):
        """记录类属性被赋值"""
        resp_info = self._response_vars.get(resp_var_name)
        if not resp_info:
            return

        self._attr_producers[attr_key] = {
            "func": resp_info["func"],
            "seq": resp_info["seq"],
            "extract_path": extract_path,
        }

        # 更新上游接口的 downstream
        for iface in self.interfaces:
            if iface["func"] == resp_info["func"] and iface["seq"] == resp_info["seq"]:
                if not iface.get("response_usage"):
                    iface["response_usage"] = {}
                iface["response_usage"]["captured_by"] = attr_key
                iface["response_usage"]["extract_path"] = extract_path
                break

    def record_local_production(self, local_name: str, resp_var_name: str, extract_path: str):
        """记录局部变量被赋值"""
        resp_info = self._response_vars.get(resp_var_name)
        if not resp_info:
            return

        self._var_producers[local_name] = {
            "func": resp_info["func"],
            "seq": resp_info["seq"],
            "extract_path": extract_path,
        }

        # 更新上游接口的 response_usage
        for iface in self.interfaces:
            if iface["func"] == resp_info["func"] and iface["seq"] == resp_info["seq"]:
                if not iface.get("response_usage"):
                    iface["response_usage"] = {}
                iface["response_usage"]["captured_by"] = local_name
                iface["response_usage"]["extract_path"] = extract_path
                break

    def resolve_arg_source(self, arg_value) -> str:
        """解析参数值的来源"""
        if not isinstance(arg_value, str):
            return "literal"
        if arg_value.startswith("<STATE:"):
            return arg_value[7:-1]  # 提取 Class.attr
        if arg_value.startswith("<变量:"):
            return arg_value[4:-1]  # 提取变量名
        return "literal"

    def find_upstream(self, args: list) -> list:
        """根据参数中的变量引用，找到上游接口"""
        upstream_funcs = set()
        for arg in args:
            if not isinstance(arg, str):
                continue
            if arg.startswith("<STATE:"):
                attr_key = arg[7:-1]
                info = self._attr_producers.get(attr_key)
                if info:
                    upstream_funcs.add(info["func"])
            elif arg.startswith("<变量:"):
                var_key = arg[4:-1].strip()
                info = self._var_producers.get(var_key)
                if info:
                    upstream_funcs.add(info["func"])
        return sorted(upstream_funcs)

    def build_state_flow(self):
        """构建完整的状态流列表"""
        # 从类属性中收集
        attr_consumers = {}  # attr_key → [consuming_func_names]
        for iface in self.interfaces:
            for arg in iface.get("args", []):
                if isinstance(arg, str) and arg.startswith("<STATE:"):
                    attr_key = arg[7:-1]
                    attr_consumers.setdefault(attr_key, []).append(iface["func"])
                elif isinstance(arg, str) and arg.startswith("<变量:"):
                    var_key = arg[4:-1].strip()
                    attr_consumers.setdefault(var_key, []).append(iface["func"])

        # 类属性状态流
        for attr_key, info in self._attr_producers.items():
            self.state_flow.append({
                "var_name": attr_key,
                "produced_by": info["func"],
                "consumed_by": attr_consumers.get(attr_key, []),
                "extract_path": info["extract_path"],
            })

        # 局部变量状态流
        for var_key, info in self._var_producers.items():
            self.state_flow.append({
                "var_name": var_key,
                "produced_by": info["func"],
                "consumed_by": attr_consumers.get(var_key, []),
                "extract_path": info["extract_path"],
            })

        # 更新所有接口的 downstream
        for sf in self.state_flow:
            for iface in self.interfaces:
                if iface["func"] == sf["produced_by"]:
                    for consumer_func in sf["consumed_by"]:
                        if consumer_func not in iface["downstream"]:
                            iface["downstream"].append(consumer_func)


def _find_chain_body(tree: ast.Module) -> list:
    """
    找到 chain 方法的语句列表。

    支持两种结构：
    1. 类方法：class XxxChain: def ws_xxx_chain(self): ...
    2. 独立函数：def ws_xxx_chain(ws_client): ...
    """
    # 优先找类方法
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if item.name.endswith("_chain"):
                        return item.body

    # 再找独立函数
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.endswith("_chain"):
                return node.body

    # 兜底：整个模块
    return tree.body


def _walk_statements(stmts: list, ctx: _WorkflowContext):
    """按顺序遍历语句，提取接口和变量追踪"""
    for stmt in stmts:
        _process_statement(stmt, ctx)


def _process_statement(stmt: ast.stmt, ctx: _WorkflowContext, depth: int = 0):
    """处理单条语句"""
    if depth > 10:
        return

    # 1. 赋值语句：resp = send_request(...) 或 var = resp["ret"][0]
    if isinstance(stmt, ast.Assign):
        _process_assign(stmt, ctx)
        return

    # 2. 表达式语句：send_request(...) 或 ClassName(...).method() 或 time.sleep(...)
    if isinstance(stmt, ast.Expr):
        _process_expr_stmt(stmt, ctx)
        return

    # 3. if 语句：if resp and resp.get("success"): ...
    if isinstance(stmt, ast.If):
        _process_if(stmt, ctx)
        return

    # 4. try/except
    if isinstance(stmt, ast.Try):
        _walk_statements(stmt.body, ctx)
        for handler in stmt.handlers:
            _walk_statements(handler.body, ctx)
        _walk_statements(stmt.orelse, ctx)
        _walk_statements(stmt.finalbody, ctx)
        return

    # 5. for/while
    if isinstance(stmt, (ast.For, ast.While)):
        _walk_statements(stmt.body, ctx)
        _walk_statements(stmt.orelse, ctx)
        return

    # 6. with
    if isinstance(stmt, ast.With):
        _walk_statements(stmt.body, ctx)
        return

    # 7. return
    if isinstance(stmt, ast.Return):
        if stmt.value:
            _walk_statements([ast.Expr(value=stmt.value)], ctx)
        return


def _process_assign(stmt: ast.Assign, ctx: _WorkflowContext):
    """处理赋值语句"""
    # 情况1：resp = send_request(...)
    if isinstance(stmt.value, ast.Call) and _is_send_request(stmt.value):
        for target in stmt.targets:
            if isinstance(target, ast.Name):
                _record_send_request(stmt.value, ctx, assign_var=target.id)
            else:
                _record_send_request(stmt.value, ctx)
        return

    # 情况2：Class.attr = resp["ret"][0] 或 var = resp["ret"][0]
    for target in stmt.targets:
        # Class.attr = ...
        if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name):
            class_name = target.value.id
            attr_name = target.attr

            # resp_var返回值，extract_path提取路径
            resp_var, extract_path = _extract_response_access(stmt.value)
            if resp_var:
                attr_key = f"{class_name}.{attr_name}"
                ctx.record_attr_production(attr_key, resp_var, extract_path)
            return

        # local_var = resp["ret"][0]
        if isinstance(target, ast.Name):
            resp_var, extract_path = _extract_response_access(stmt.value)
            if resp_var:
                ctx.record_local_production(target.id, resp_var, extract_path)
            return

    # 情况3：instance = ClassName(...)  (不处理，但需遍历)
    if isinstance(stmt.value, ast.Call):
        _check_sub_workflow(stmt.value, ctx)


def _process_expr_stmt(stmt: ast.Expr, ctx: _WorkflowContext):
    """处理表达式语句"""
    call = stmt.value
    if not isinstance(call, ast.Call):
        return

    # send_request(...)
    if _is_send_request(call):
        _record_send_request(call, ctx)
        return

    # ClassName(...).method()  — 子工作流调用
    if isinstance(call.func, ast.Attribute):
        inner = call.func.value
        if isinstance(inner, ast.Call):
            _check_sub_workflow_chain(call, ctx)
            return

    # time.sleep(N)
    if isinstance(call.func, ast.Attribute):
        if (isinstance(call.func.value, ast.Name) and
                call.func.value.id == "time" and
                call.func.attr == "sleep"):
            # 不需要在这里记录，control_flow 单独处理
            return


def _process_if(stmt: ast.If, ctx: _WorkflowContext):
    """处理 if 语句"""
    _walk_statements(stmt.body, ctx)
    _walk_statements(stmt.orelse, ctx)


def _extract_response_access(node: ast.expr) -> tuple:
    """
    从赋值右值中提取响应变量名和访问路径。

    例：resp["ret"][0] → ("resp", "resp['ret'][0]")
    例：resp.get("ret", []) → ("resp", "resp.get('ret', [])")
    """
    # resp["ret"][0]  — Subscript(Subscript(Name("resp"), "ret"), 0)
    if isinstance(node, ast.Subscript):
        var_name, path = _extract_response_access(node.value)
        if var_name:
            key = _get_subscript_key(node)
            path = f"{path}[{key}]" if key else path
            return var_name, path
        return None, None

    # resp.get("ret", [...])
    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            var_name, _ = _extract_response_access(node.func.value)
            if var_name and node.args:
                key = _extract_const_value(node.args[0])
                return var_name, f"resp.get('{key}')" if isinstance(key, str) else "resp.get(...)"
        return None, None

    # 基础情况：变量名
    if isinstance(node, ast.Name):
        return node.id, node.id

    return None, None


def _get_subscript_key(node: ast.Subscript) -> str:
    """获取下标访问的键值"""
    key = _extract_const_value(node.slice)
    if key is not None:
        if isinstance(key, str):
            return f"'{key}'"
        return str(key)
    return ""


def _record_send_request(call: ast.Call, ctx: _WorkflowContext, assign_var: str = None):
    """记录一个 send_request 调用"""
    if len(call.args) < 4:
        return

    func_name = _extract_str(call.args[1])
    if not func_name:
        return

    raw_args = _extract_args(call.args[2])
    desc = _extract_str(call.args[3]) or ""

    seq = ctx.seq
    call_type = "capture_response" if assign_var else "fire_and_forget"

    # 构建 args_detail
    args_detail = []
    for i, arg in enumerate(raw_args):
        source = "literal"
        if isinstance(arg, str):
            if arg.startswith("<STATE:"):
                source = f"state:{arg[7:-1]}"
            elif arg.startswith("<变量:"):
                source = f"state:{arg[4:-1]}"
        args_detail.append({"index": i, "value": arg, "source": source})

    # 查找 upstream
    upstream = ctx.find_upstream(raw_args)

    iface = {
        "seq": seq,
        "func": func_name,
        "desc": desc,
        "call_type": call_type,
        "args_detail": args_detail,
        "args": raw_args,
        "response_usage": None,
        "upstream": upstream,
        "downstream": [],
    }
    ctx.interfaces.append(iface)

    # 如果有赋值变量，记录响应捕获
    if assign_var:
        ctx.record_response_capture(assign_var, seq, func_name)


def _check_sub_workflow(call: ast.Call, ctx: _WorkflowContext):
    """检测 ClassName(args) 实例化"""
    if isinstance(call.func, ast.Name):
        class_name = call.func.id
        if class_name in ("send_request", "logger", "print", "time"):
            return
        # 记录实例化（可能后续有 .method() 调用）
        ctx.sub_workflows.append({
            "target_class": class_name,
            "passed_params": _extract_call_kwargs(call),
        })


def _check_sub_workflow_chain(call: ast.Call, ctx: _WorkflowContext):
    """
    检测 ClassName(...).method() 形式的子工作流调用。

    例：GetAll4(ws_client=self.ws_client).ws_getall4_chain()
    """
    inner_call = call.func.value
    method_name = call.func.attr

    if not isinstance(inner_call, ast.Call):
        return

    class_name = None
    if isinstance(inner_call.func, ast.Name):
        class_name = inner_call.func.id
    elif isinstance(inner_call.func, ast.Attribute):
        return  # self.xxx() 不是子工作流

    if not class_name or class_name in ("send_request", "logger", "print", "time"):
        return

    ctx.sub_workflows.append({
        "target_class": class_name,
        "target_method": method_name,
        "source_file": f"Service.{class_name.lower()}.py",
        "passed_params": _extract_call_kwargs(inner_call),
    })


def _extract_call_kwargs(call: ast.Call) -> dict:
    """提取函数调用的关键字参数"""
    params = {}
    for kw in call.keywords:
        if kw.arg and isinstance(kw.value, ast.Name):
            params[kw.arg] = kw.value.id
        elif kw.arg and isinstance(kw.value, ast.Attribute):
            params[kw.arg] = _unparse(kw.value)
        elif kw.arg:
            try:
                params[kw.arg] = _unparse(kw.value)
            except Exception:
                params[kw.arg] = "?"
    return params


def _analyze_control_flow(body: list) -> dict:
    """分析控制流结构"""
    result = {
        "has_try_except": False,
        "delays": [],
        "conditionals": [],
    }

    for stmt in ast.walk(ast.Module(body=body, type_ignores=[])):
        # try/except
        if isinstance(stmt, ast.Try):
            result["has_try_except"] = True

        # time.sleep(N)
        if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Call):
            call = stmt.value
            if (isinstance(call.func, ast.Attribute) and
                    isinstance(call.func.value, ast.Name) and
                    call.func.value.id == "time" and
                    call.func.attr == "sleep"):
                if call.args:
                    seconds = _extract_const_value(call.args[0])
                    if seconds is not None:
                        result["delays"].append({"seconds": seconds})

        # if resp and resp.get("success") — 条件分支
        if isinstance(stmt, ast.If):
            cond_desc = _describe_condition(stmt.test)
            if cond_desc:
                result["conditionals"].append({"condition": cond_desc})

    return result


def _describe_condition(node: ast.expr) -> str:
    """将 if 条件简化为可读描述"""
    # if resp and resp.get("success") and ...
    parts = []
    _collect_condition_parts(node, parts)
    if parts:
        return " and ".join(parts[:3])  # 只取前 3 个关键条件
    return _unparse(node) if node else ""


def _collect_condition_parts(node: ast.expr, parts: list):
    """递归收集条件表达式的关键部分"""
    if isinstance(node, ast.BoolOp):
        for val in node.values:
            _collect_condition_parts(val, parts)
        return

    if isinstance(node, ast.Call):
        desc = _unparse(node)
        if len(desc) < 80:
            parts.append(desc)
        return

    if isinstance(node, ast.Name):
        parts.append(node.id)
        return

    if isinstance(node, ast.Compare):
        parts.append(_unparse(node))
        return


# ==================== AST 辅助函数 ====================

def _is_send_request(call_node) -> bool:
    """判断 AST Call 节点是否是 send_request(...)"""
    return isinstance(call_node.func, ast.Name) and call_node.func.id == "send_request"


def _extract_str(node) -> Optional[str]:
    """提取字符串常量"""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_const_value(node):
    """提取常量值"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        val = _extract_const_value(node.operand)
        if val is not None:
            return -val
    return None


def _extract_args(node) -> list:
    """提取参数列表"""
    if isinstance(node, ast.List):
        return [_eval_const(elt) for elt in node.elts]
    return []


def _eval_const(node):
    """求值常量表达式，无法求值的标记为占位符"""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_eval_const(e) for e in node.elts]
    if isinstance(node, ast.Dict):
        return dict(zip(
            (_eval_const(k) for k in node.keys),
            (_eval_const(v) for v in node.values),
        ))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return -_eval_const(node.operand)
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"<STATE:{node.value.id}.{node.attr}>"
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
        if node.args and isinstance(node.args[0], ast.Attribute):
            inner = node.args[0]
            if isinstance(inner.value, ast.Name):
                return f"<STATE:{inner.value.id}.{inner.attr}>"
    if isinstance(node, ast.Name):
        return f"<变量: {node.id}>"
    if isinstance(node, ast.ListComp):
        return "<列表推导式>"
    try:
        return f"<表达式: {_unparse(node)}>"
    except Exception:
        return "<表达式>"


# ==================== CLI ====================

def parse_workflow_dir(dir_path: str) -> list:
    """解析 Service 目录下所有 chain 文件"""
    workflows = []
    for filename in sorted(os.listdir(dir_path)):
        if not filename.endswith("_chain.py"):
            continue
        workflows.append(parse_workflow(os.path.join(dir_path, filename)))
    return workflows


if __name__ == "__main__":
    import sys
    service_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Service")

    if len(sys.argv) > 1:
        source = sys.argv[1]
        target = source if source.endswith(".py") else os.path.join(service_dir, f"{source}_chain.py")
    else:
        target = os.path.join(service_dir, "loadmodel_chain.py")

    print("===== 轻量版 =====")
    wf = parse_workflow(target)
    print(json.dumps(wf, ensure_ascii=False, indent=2))

    print("\n===== 增强版 =====")
    wf2 = parse_workflow_enhanced(target)
    # 去掉 source_code 以便阅读
    wf2_display = {k: v for k, v in wf2.items() if k != "source_code"}
    print(json.dumps(wf2_display, ensure_ascii=False, indent=2))
