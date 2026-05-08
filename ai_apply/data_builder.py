"""
测试数据生成器（确定性）

根据语义分析的参数约束，为不同类型的测试场景自动生成具体参数值。
不依赖 LLM，纯确定性代码。

用法:
    from data_builder import TestDataBuilder

    builder = TestDataBuilder(semantics)
    builder.fill(scenarios)
"""

import re


class TestDataBuilder:
    """根据参数约束为测试场景生成具体测试数据"""

    # __init__ 是初始化方法，创建对象时自动执行，用来"装数据"
    def __init__(self, semantics: dict):
        self.params_map = {}
        for iface in semantics.get("interfaces", []):
            func = iface.get("func", "")
            params = iface.get("params", [])
            self.params_map[func] = params

    # self 就是"这个对象自己"，让类里的方法能共享变量和其他方法
    def fill(self, scenarios: dict) -> dict:
        """遍历场景，根据类别和参数约束填充 args"""
        for iface in scenarios.get("interfaces", []):
            func = iface.get("func", "")
            constraints = self.params_map.get(func, [])

            for scenario in iface.get("test_scenarios", []):
                scenario["args"] = self._build_args(
                    scenario.get("category", "normal"), constraints, scenario
                )

        return scenarios

    def _build_args(self, category: str, constraints: list, scenario: dict) -> list:
        if category == "invalid_func":
            return []
        if not constraints:
            return []

        if category == "normal":
            return self._normal_args(constraints)
        if category == "boundary":
            return self._boundary_args(constraints, scenario)
        if category == "wrong_arg_type":
            return self._wrong_type_args(constraints, scenario)
        if category == "missing_args":
            return self._missing_args(constraints)
        if category == "null_args":
            return self._null_args(constraints, scenario)
        if category == "violation":
            return self._violation_args(constraints, scenario)

        return self._normal_args(constraints)

    def _normal_args(self, constraints: list) -> list:
        args = []
        for p in constraints:
            ptype = p.get("type", "str")
            valid_range = p.get("valid_range", "")
            enum_vals = p.get("enum_values", [])

            if enum_vals and isinstance(enum_vals, list) and len(enum_vals) > 0:
                val = enum_vals[0]
                if isinstance(val, str):
                    try:
                        val = int(val)
                    except (ValueError, TypeError):
                        pass
                args.append(val)
                continue

            range_min, range_max = _parse_range(valid_range)
            if range_min is not None and range_max is not None:
                args.append((range_min + range_max) // 2)
                continue

            args.append(_get_type_default(ptype))
        return args

    def _boundary_args(self, constraints: list, scenario: dict) -> list:
        args = self._normal_args(constraints)

        target_idx = None
        boundary_val = None
        for p in constraints:
            bv = p.get("boundary_values", [])
            if bv and isinstance(bv, list):
                target_idx = p.get("index", 0)
                boundary_val = bv[0]
                if isinstance(boundary_val, str):
                    try:
                        boundary_val = int(boundary_val)
                    except (ValueError, TypeError):
                        pass
                break
            valid_range = p.get("valid_range", "")
            rmin, rmax = _parse_range(valid_range)
            if rmin is not None:
                target_idx = p.get("index", 0)
                boundary_val = rmin - 1
                break

        if target_idx is not None and boundary_val is not None and target_idx < len(args):
            args[target_idx] = boundary_val

        return args

    def _wrong_type_args(self, constraints: list, scenario: dict) -> list:
        args = self._normal_args(constraints)
        for i, p in enumerate(constraints):
            ptype = p.get("type", "")
            if ptype:
                args[i] = _get_wrong_type_value(ptype)
                break
        return args

    def _missing_args(self, constraints: list) -> list:
        required_indices = [
            p.get("index", i) for i, p in enumerate(constraints)
            if p.get("required") == 0
        ]
        if not required_indices:
            return []

        args = self._normal_args(constraints)
        drop_idx = required_indices[0]
        if drop_idx < len(args):
            args.pop(drop_idx)
        return args

    def _null_args(self, constraints: list, scenario: dict) -> list:
        args = self._normal_args(constraints)
        for i, p in enumerate(constraints):
            if p.get("required") == 0 and i < len(args):
                args[i] = None
                break
        else:
            if args:
                args[0] = None
        return args

    def _violation_args(self, constraints: list, scenario: dict) -> list:
        args = self._normal_args(constraints)
        if args:
            ptype = constraints[0].get("type", "") if constraints else ""
            if "int" in ptype.lower():
                args[0] = -999
            elif "str" in ptype.lower():
                args[0] = ""
            else:
                args[0] = -1
        return args


# ==================== 工具函数 ====================

def _parse_range(range_str: str) -> tuple:
    """解析范围字符串，返回 (min, max)"""
    if not range_str:
        return None, None
    range_str = range_str.strip()
    m = re.match(r'(-?\d+)\s*[-~到]\s*(-?\d+)', range_str)
    if m:
        return int(m.group(1)), int(m.group(2))
    return None, None


def _get_type_default(type_str: str):
    """获取类型的合法默认值"""
    t = (type_str or "").lower().strip()
    if "int" in t:
        return 0
    if "float" in t or "double" in t:
        return 0.0
    if "bool" in t:
        return True
    if "list" in t or "array" in t:
        return []
    if "dict" in t or "map" in t or "object" in t:
        return {}
    return ""


def _get_wrong_type_value(type_str: str):
    """获取错误类型的值"""
    t = (type_str or "").lower().strip()
    if "int" in t or "float" in t:
        return "not_a_number"
    if "str" in t:
        return 12345
    if "bool" in t:
        return "not_bool"
    if "list" in t:
        return "not_a_list"
    return "wrong_type"
