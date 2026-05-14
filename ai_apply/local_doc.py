"""
本地 MD 接口文档查找模块

从 后端接口文档.md 中按接口名定位文档片段，解析参数和描述信息。
返回格式与 DingTalkDocClient.get_interface_docs() 一致，可直接替换使用。

用法:
    from local_doc import LocalDocClient

    client = LocalDocClient()
    docs = client.get_interface_docs(["sim.loadModel", "simArcs.webGetHandleType"])
"""

import os
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger("local_doc")

# 接口名匹配模式：sim.xxx 或 simArcs.xxx 等
_IFACE_PATTERN = re.compile(
    r"^(sim\.\w+|simArcs\.\w+|simIK\.\w+|simAssimp\.\w+|wsRemoteApi\.\w+)$"
)

# 参数表行：| param_name | description |
_TABLE_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|$")


class LocalDocClient:
    """本地 MD 文档查找客户端"""

    def __init__(self, doc_path: str = None):
        if doc_path is None:
            doc_path = os.path.join(os.path.dirname(__file__), "后端接口文档.md")
        self.doc_path = doc_path
        self._content = None
        self._positions = None  # {func_name: line_index}

    def _load(self):
        """懒加载文档并建立索引"""
        if self._content is not None:
            return

        if not os.path.exists(self.doc_path):
            logger.warning("本地文档不存在: %s", self.doc_path)
            self._content = []
            self._positions = {}
            return

        with open(self.doc_path, "r", encoding="utf-8") as f:
            self._content = f.readlines()

        # 建立接口名 → 行号的索引
        self._positions = {}
        for i, line in enumerate(self._content):
            stripped = line.strip()
            if _IFACE_PATTERN.match(stripped):
                if stripped not in self._positions:
                    self._positions[stripped] = i

        logger.info("本地文档索引完成: %d 个接口 (%s)",
                     len(self._positions), self.doc_path)

    def get_interface_docs(
        self,
        interface_names: List[str],
        **kwargs,
    ) -> Dict[str, Dict]:
        """
        根据接口名列表获取文档信息。

        Returns:
            {
                "sim.loadModel": {
                    "func": "sim.loadModel",
                    "description": "...",
                    "params": [{"name": "file_path", "description": "模型文件路径"}],
                    "request_example": "...",
                    "response_example": "...",
                    "source": "local_md",
                }
            }
        """
        self._load()

        results = {}
        for name in interface_names:
            pos = self._positions.get(name)
            if pos is None:
                logger.debug("本地文档未找到: %s", name)
                continue

            doc = self._parse_block(name, pos)
            if doc:
                doc["source"] = "local_md"
                results[name] = doc

        logger.info("本地文档匹配: %d/%d 个接口",
                     len(results), len(interface_names))
        return results

    def _parse_block(self, func_name: str, start_line: int) -> Optional[Dict]:
        """从 start_line 开始解析，直到遇到下一个接口名或文档结束"""
        lines = self._content
        end_line = len(lines)

        # 找到下一个接口名的位置
        for i in range(start_line + 1, len(lines)):
            if _IFACE_PATTERN.match(lines[i].strip()):
                end_line = i
                break

        block = "".join(lines[start_line:end_line])

        # 解析各部分
        params = self._parse_params(block)
        request_example = self._extract_json(block, "Request:")
        response_example = self._extract_json(block, "Response:")
        description = self._extract_description(block)

        return {
            "func": func_name,
            "description": description,
            "params": params,
            "request_example": request_example,
            "response_example": response_example,
        }

    def _parse_params(self, block: str) -> List[Dict]:
        """解析参数表（Request 和 Response 的参数都会提取）"""
        params = []
        in_param_table = False

        for line in block.split("\n"):
            stripped = line.strip()

            # 跳过表头和分隔行
            if stripped.startswith("| 参数名称") or stripped.startswith("| ---"):
                in_param_table = True
                continue

            if not in_param_table:
                continue

            m = _TABLE_ROW.match(stripped)
            if m:
                param_name = m.group(1).strip()
                param_desc = m.group(2).strip()
                # 跳过空行
                if param_name and param_name != "---":
                    # 清理 HTML 标签和转义
                    param_desc = _clean_text(param_desc)
                    param_name = _clean_text(param_name)
                    params.append({
                        "name": param_name,
                        "description": param_desc,
                    })
            elif stripped and not stripped.startswith("|"):
                # 遇到非表格行，结束当前参数表
                in_param_table = False

        return params

    def _extract_json(self, block: str, section: str) -> str:
        """提取 Request/Response 部分的 JSON 示例"""
        idx = block.find(section)
        if idx < 0:
            return ""

        # 找 JSON 开始位置
        json_start = block.find("{", idx)
        if json_start < 0:
            return ""

        # 简单提取到大括号结束
        depth = 0
        json_end = json_start
        for i in range(json_start, min(json_start + 2000, len(block))):
            if block[i] == "{":
                depth += 1
            elif block[i] == "}":
                depth -= 1
                if depth == 0:
                    json_end = i + 1
                    break

        return block[json_start:json_end]

    def _extract_description(self, block: str) -> str:
        """提取接口描述（标题行到 Request 之间的文字）"""
        lines = block.split("\n")
        desc_parts = []
        for line in lines[1:]:  # 跳过接口名本身
            stripped = line.strip()
            if stripped.startswith("Request:") or stripped.startswith("|"):
                break
            if stripped and not stripped.startswith("#"):
                desc_parts.append(stripped)
        return "\n".join(desc_parts)


def _clean_text(text: str) -> str:
    """清理 MD 表格中的 HTML 标签和转义字符"""
    # 去掉 <br> 标签，换成换行
    text = re.sub(r"<br\s*/?>", "\n", text)
    # 去掉其他 HTML 标签
    text = re.sub(r"<[^>]+>", "", text)
    # 反转义
    text = text.replace("\\[", "[").replace("\\]", "]")
    text = text.replace("\\_", "_")
    text = text.replace("\\*", "*")
    return text.strip()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO)
    client = LocalDocClient()

    # 测试
    test_names = [
        "sim.loadModel",
        "simArcs.webGetHandleType",
        "simArcs.ahmCreateHierarchyElement",
        "sim.getObjectPosition",
        "simArcs.webMoveObject",
        "simArcs.ahmSetElementParent",
        "simArcs.ahmGetHierarchy",
    ]
    docs = client.get_interface_docs(test_names)

    for name, doc in docs.items():
        print(f"\n{'=' * 50}")
        print(f"接口: {name}")
        print(f"描述: {doc['description'][:100]}")
        print(f"参数:")
        for p in doc.get("params", []):
            print(f"  - {p['name']}: {p['description'][:80]}")
        print(f"来源: {doc['source']}")
