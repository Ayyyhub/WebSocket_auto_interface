"""
钉钉文档查询 Skills 模块
- 按需精准获取接口文档
- 双重缓存更新策略：TTL 时间过期 + 手动强制刷新
- 本地索引映射接口名到文档位置

用法:
    from skills.dingtalk_doc_skill import DingTalkDocClient
    
    skill = DingTalkDocClient()
    
    # 普通查询（使用缓存）
    docs = skill.get_interface_docs(["amStart", "ahmGetHierarchy"])
    
    # 强制刷新缓存
    docs = skill.get_interface_docs(["amStart"], force_refresh=True)
"""

import json
import os
import re
import time
import yaml
import requests
from typing import Dict, List, Optional
from pathlib import Path
from datetime import datetime


class DingTalkDocClient:
    """钉钉文档查询技能 - 支持缓存和索引机制"""
    
    def __init__(
        self,
        cache_dir: str = None,
        ttl_hours: int = 24,
        doc_token: str = None,
        doc_key: str = None,
        operator_id: str = None,
        corp_id: str = None,
        app_key: str = None,
        app_secret: str = None
    ):
        """
        初始化钉钉文档查询模块
        
        Args:
            cache_dir: 缓存目录路径
            ttl_hours: 缓存有效期（小时），默认 24 小时
            doc_token: 钉钉文档访问令牌 (access_token)
            doc_key: 钉钉文档标识符 (dentryUuid)
            operator_id: 操作者 ID (unionId 或 staffId)
            corp_id: 企业 ID (CORPID)
            app_key: 企业内部应用的 AppKey
            app_secret: 企业内部应用的 AppSecret
        """
        self.cache_dir = Path(cache_dir) if cache_dir else Path(__file__).parent.parent / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.ttl_seconds = ttl_hours * 3600
        self.doc_token = doc_token
        self.doc_key = doc_key
        self.operator_id = operator_id
        self.corp_id = corp_id
        self.app_key = app_key
        self.app_secret = app_secret
        
        # 钉钉 API 基础 URL
        self.dingtalk_api_base = "https://api.dingtalk.com"
        self.dingtalk_oapi_base = "https://oapi.dingtalk.com"
        
        # 缓存文件路径
        self.index_file = self.cache_dir / "doc_index.json"
        self.content_cache_file = self.cache_dir / "doc_content_cache.json"
        
        # 内存缓存
        self._index_cache = None
        self._content_cache = None
        self._full_doc_cache = None  # 缓存完整文档，避免重复请求
        self._token_cache = None  # 缓存 access_token
        self._token_expire_time = 0

        # 自动从配置文件加载（如果未显式传入）
        if not self.app_key:
            self._load_config()
    
    def _load_config(self):
        """从 config/dingtalk_config.yaml 加载钉钉 API 凭证"""
        config_path = Path(__file__).parent.parent.parent / "config" / "dingtalk_config.yaml"
        if not config_path.exists():
            print(f"⚠️  钉钉配置文件不存在: {config_path}")
            return

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)

            if not self.app_key:
                self.app_key = config.get("app_key")
            if not self.app_secret:
                self.app_secret = config.get("app_secret")
            if not self.doc_key:
                self.doc_key = config.get("doc_key")
            if not self.corp_id:
                self.corp_id = config.get("corp_id")
            if not self.operator_id:
                self.operator_id = config.get("operator_id")

            # 从配置文件读取 TTL
            if config.get("cache_ttl_hours"):
                self.ttl_seconds = config["cache_ttl_hours"] * 3600

            print(f"✅ 已从配置文件加载钉钉凭证 (doc_key={self.doc_key})")
        except Exception as e:
            print(f"⚠️  加载钉钉配置失败: {e}")

    def _get_access_token(self) -> str:
        """
        获取 access_token（自动刷新）
        
        优先使用缓存的 token，如果过期则重新获取
        """
        import time
        
        # 检查缓存的 token 是否有效（提前 5 分钟刷新）
        if self._token_cache and time.time() < self._token_expire_time - 300:
            return self._token_cache
        
        if not self.app_key or not self.app_secret:
            if self.doc_token:
                print("⚠️  使用手动提供的 access_token（可能已过期）")
                return self.doc_token
            else:
                raise ValueError("缺少 app_key/app_secret 或 doc_token")
        
        # 获取新的 access_token
        print("🔄 正在获取新的 access_token...")
        url = f"{self.dingtalk_oapi_base}/gettoken"
        params = {
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            result = response.json()
            
            if result.get("errcode") == 0:
                self._token_cache = result.get("access_token")
                expires_in = result.get("expires_in", 7200)
                self._token_expire_time = time.time() + expires_in
                print(f"✅ access_token 获取成功（有效期 {expires_in} 秒）")
                return self._token_cache
            else:
                print(f"❌ 获取 access_token 失败: {result.get('errmsg')}")
                return None
        except Exception as e:
            print(f"❌ 获取 access_token 异常: {e}")
            return None
    
    def get_interface_docs(
        self,
        interface_names: List[str],
        force_refresh: bool = False,
        refresh_if_missing: bool = True
    ) -> Dict[str, Dict]:
        """
        获取接口文档信息（核心方法）
        
        Args:
            interface_names: 接口名称列表，如 ["amStart", "ahmGetHierarchy"]
            force_refresh: 强制刷新缓存（忽略 TTL）
            refresh_if_missing: 如果索引中缺少接口，是否自动刷新
        
        Returns:
            {
                "amStart": {
                    "method": "POST",
                    "path": "/api/v1/amStart",
                    "params": [...],
                    "description": "...",
                    "source": "cache|api"
                },
                ...
            }
        """
        print(f"\n📖 开始获取 {len(interface_names)} 个接口文档...")
        
        # 1. 加载索引
        index = self._load_index(force_refresh=force_refresh)
        
        # 2. 检查索引覆盖度
        missing_names = [name for name in interface_names if name not in index.get("interfaces", {})]
        
        if missing_names:
            print(f"⚠️  索引中缺少 {len(missing_names)} 个接口: {missing_names}")
            
            if refresh_if_missing or force_refresh:
                print("🔄 自动刷新文档索引...")
                index = self._refresh_index()
                missing_names = [name for name in interface_names if name not in index.get("interfaces", {})]
                
                if missing_names:
                    print(f"❌ 刷新后仍找不到: {missing_names}")
            else:
                print(f"💡 提示: 使用 force_refresh=True 或 refresh_if_missing=True 自动获取缺失接口")
        
        # 3. 根据索引获取接口详情
        results = {}
        cached_content = self._load_content_cache()
        
        for name in interface_names:
            if name not in index.get("interfaces", {}):
                print(f"  ⏭️  跳过 {name}（索引中不存在）")
                continue
            
            interface_meta = index["interfaces"][name]
            
            # 检查内容缓存
            if name in cached_content and not force_refresh:
                cache_time = cached_content[name].get("cached_at", 0)
                if time.time() - cache_time < self.ttl_seconds:
                    results[name] = cached_content[name]["data"]
                    results[name]["source"] = "cache"
                    print(f"  ✅ {name} (来自缓存)")
                    continue
            
            # 从 API 获取
            print(f"  📥 {name} (从钉钉API获取)...")
            doc_content = self._fetch_interface_from_dingtalk(interface_meta)
            
            if doc_content:
                results[name] = doc_content
                results[name]["source"] = "api"
                # 更新内容缓存
                self._update_content_cache(name, doc_content)
            else:
                print(f"  ❌ 获取 {name} 失败")
        
        success_count = len(results)
        print(f"\n✅ 成功获取 {success_count}/{len(interface_names)} 个接口文档")
        
        return results
    
    def refresh_all(self) -> Dict:
        """
        强制刷新所有文档（手动更新策略）
        
        Returns:
            完整的索引数据
        """
        print("\n🔄 强制刷新所有文档缓存...")
        return self._refresh_index()
    
    def get_cache_status(self) -> Dict:
        """获取缓存状态信息"""
        status = {
            "index_exists": self.index_file.exists(),
            "content_cache_exists": self.content_cache_file.exists(),
            "interfaces_count": 0,
            "cache_age_hours": None,
            "ttl_hours": self.ttl_seconds / 3600,
            "is_expired": False
        }
        
        if self.index_file.exists():
            index = self._load_index()
            status["interfaces_count"] = len(index.get("interfaces", {}))
            
            if "last_sync" in index:
                sync_time = datetime.fromisoformat(index["last_sync"])
                age = datetime.now() - sync_time
                status["cache_age_hours"] = age.total_seconds() / 3600
                status["is_expired"] = age.total_seconds() > self.ttl_seconds
        
        return status
    
    # ========== 内部方法 ==========
    
    def _load_index(self, force_refresh: bool = False) -> Dict:
        """加载文档索引"""
        if self._index_cache and not force_refresh:
            return self._index_cache
        
        if not force_refresh and self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    index = json.load(f)
                
                # 检查 TTL
                if "last_sync" in index:
                    sync_time = datetime.fromisoformat(index["last_sync"])
                    age_seconds = (datetime.now() - sync_time).total_seconds()
                    
                    if age_seconds < self.ttl_seconds:
                        print(f"✅ 使用缓存索引（{age_seconds/3600:.1f} 小时前同步）")
                        self._index_cache = index
                        return index
                    else:
                        print(f"⏰ 索引已过期（{age_seconds/3600:.1f} 小时，TTL: {self.ttl_seconds/3600} 小时）")
                else:
                    self._index_cache = index
                    return index
            except Exception as e:
                print(f"⚠️  读取索引失败: {e}")
        
        # 索引不存在或已过期，刷新
        return self._refresh_index()
    
    def _refresh_index(self) -> Dict:
        """刷新文档索引（从钉钉 API 获取）"""
        print("📡 正在从钉钉 API 获取文档...")
        
        # 调用钉钉 API 获取完整文档
        full_doc = self._fetch_full_document_from_dingtalk()
        
        if not full_doc:
            print("❌ 获取文档失败，返回空索引")
            return {"interfaces": {}, "last_sync": datetime.now().isoformat()}
        
        # 解析文档，提取所有接口信息
        index = self._parse_document_to_index(full_doc)
        index["last_sync"] = datetime.now().isoformat()
        
        # 保存索引
        self._save_index(index)
        print(f"✅ 索引已更新，共 {len(index.get('interfaces', {}))} 个接口")
        
        return index
    
    def _fetch_full_document_from_dingtalk(self) -> Optional[Dict]:
        """
        从钉钉 API 获取完整文档内容

        尝试多个 API 端点：
        1. GET /v1.0/doc/nodes/{docKey} - 获取节点信息
        2. GET /v1.0/doc/documents/{docKey} - 获取文档内容
        """
        print("🔌 调用钉钉文档 API...")

        token = self._get_access_token()
        if not token:
            print("❌ 无法获取 access_token")
            return None

        headers = {
            "x-acs-dingtalk-access-token": token,
            "Content-Type": "application/json"
        }

        endpoints = [
            {
                "name": "获取节点信息",
                "method": "GET",
                "url": f"{self.dingtalk_api_base}/v1.0/doc/nodes/{self.doc_key}",
                "params": {"operatorId": self.operator_id},
            },
            {
                "name": "获取文档内容",
                "method": "GET",
                "url": f"{self.dingtalk_api_base}/v1.0/doc/documents/{self.doc_key}",
                "params": {},
            },
        ]

        for ep in endpoints:
            try:
                print(f"📤 [{ep['name']}] {ep['url']}")
                if ep["method"] == "GET":
                    resp = requests.get(ep["url"], headers=headers,
                                        params=ep.get("params"), timeout=30)
                else:
                    resp = requests.post(ep["url"], headers=headers,
                                         json=ep.get("params"), timeout=30)

                if resp.status_code == 200:
                    result = resp.json()
                    # 检查是否是有效内容（非空且非错误响应）
                    if result:
                        print(f"✅ [{ep['name']}] 响应成功")
                        # 打印响应结构便于调试
                        resp_keys = list(result.keys()) if isinstance(result, dict) else type(result).__name__
                        print(f"   响应键: {resp_keys}")
                        self._full_doc_cache = result
                        return result
                else:
                    print(f"   状态码 {resp.status_code}, 跳过")
            except Exception as e:
                print(f"   请求异常: {e}")
                continue

        print("❌ 所有端点均未返回有效内容")
        return None
    
    def _fetch_interface_from_dingtalk(self, interface_meta: Dict) -> Optional[Dict]:
        """
        根据元数据精准获取单个接口详情
        
        如果文档支持按节点获取，这里可以精准请求特定节点
        """
        # 如果缓存了完整文档，直接从缓存中提取
        if self._full_doc_cache:
            return self._extract_interface_from_doc(self._full_doc_cache, interface_meta)
        
        # 否则重新获取
        full_doc = self._fetch_full_document_from_dingtalk()
        if not full_doc:
            return None
        
        # 从文档中提取指定接口
        return self._extract_interface_from_doc(full_doc, interface_meta)
    
    def _parse_document_to_index(self, full_doc: Dict) -> Dict:
        """
        解析钉钉文档，建立接口索引

        支持多种钉钉文档响应格式：
        - blocks 格式: {blocks: [{blockType, ...}]}
        - result.data 格式: {result: {data: [...]}}
        - node.content 格式: {node: {content: {blocks: [...]}}}
        - 兼容旧的 sheets/cells 格式

        Returns:
            {
                "interfaces": {
                    "sim.loadModel": {
                        "description": "...",
                        "params": [...],
                    }
                }
            }
        """
        index = {"interfaces": {}}
        if not full_doc:
            return index

        # 1. 提取所有文档块
        blocks = self._extract_all_blocks(full_doc)

        if not blocks:
            # 2. 尝试从纯文本内容解析
            text_content = self._extract_text_content(full_doc)
            if text_content:
                return self._parse_text_to_index(text_content)

            # 3. 兜底：保存原始响应到调试文件
            debug_path = self.cache_dir / "raw_api_response.json"
            with open(debug_path, "w", encoding="utf-8") as f:
                json.dump(full_doc, f, ensure_ascii=False, indent=2)
            print(f"⚠️  无法识别文档结构，原始响应已保存到 {debug_path}")
            print(f"   响应顶层键: {list(full_doc.keys()) if isinstance(full_doc, dict) else '非dict'}")
            return index

        # 4. 遍历 blocks，按 heading 识别接口
        current_iface = None
        iface_blocks = []

        for block in blocks:
            text = self._get_block_text(block)
            block_type = block.get("blockType", "")

            if block_type == "heading" and self._is_interface_name(text):
                # 保存上一个接口
                if current_iface:
                    self._add_interface_to_index(index, current_iface, iface_blocks)
                current_iface = text.strip()
                iface_blocks = []
            elif current_iface:
                iface_content = self._get_block_text(block)
                # 也检查 paragraph 中的接口名（有些文档格式不同）
                if block_type == "paragraph" and self._is_interface_name(iface_content):
                    if current_iface:
                        self._add_interface_to_index(index, current_iface, iface_blocks)
                    current_iface = iface_content.strip()
                    iface_blocks = []
                else:
                    iface_blocks.append(block)

        # 保存最后一个接口
        if current_iface:
            self._add_interface_to_index(index, current_iface, iface_blocks)

        return index

    def _extract_interface_from_doc(self, full_doc: Dict, interface_meta: Dict) -> Optional[Dict]:
        """从完整文档中提取指定接口的详细信息"""
        blocks = self._extract_all_blocks(full_doc)

        if not blocks:
            # 兜底：直接返回索引中的元数据
            return interface_meta

        target_name = interface_meta.get("func") or interface_meta.get("name", "")

        # 遍历 blocks 找到目标接口
        found = False
        content_blocks = []

        for block in blocks:
            text = self._get_block_text(block)
            block_type = block.get("blockType", "")

            if (block_type == "heading" or block_type == "paragraph") and text.strip() == target_name:
                found = True
                continue

            if found:
                # 遇到下一个接口名则停止
                if (block_type == "heading" and self._is_interface_name(text)):
                    break
                content_blocks.append(block)

        if not found:
            return interface_meta

        # 提取详细信息
        result = {"func": target_name}
        description_parts = []
        params = []

        for block in content_blocks:
            block_type = block.get("blockType", "")

            if block_type == "paragraph":
                text = self._get_block_text(block)
                if text:
                    description_parts.append(text)
            elif block_type == "table":
                table_params = self._parse_table_block(block)
                params.extend(table_params)
            elif block_type == "unorderedList" or block_type == "orderedList":
                text = self._get_block_text(block)
                if text:
                    description_parts.append(f"- {text}")

        result["description"] = "\n".join(description_parts)
        result["params"] = params

        return result

    # ========== 文档块解析辅助方法 ==========

    def _extract_all_blocks(self, doc) -> list:
        """从不同格式的钉钉 API 响应中提取所有文档块"""
        if not doc:
            return []

        if isinstance(doc, list):
            return doc

        if not isinstance(doc, dict):
            return []

        # 格式1: {blocks: [...]}
        if "blocks" in doc:
            return doc["blocks"]

        # 格式2: {result: {data: [...]}} 或 {result: {blocks: [...]}}
        result = doc.get("result", {})
        if isinstance(result, dict):
            if "data" in result:
                data = result["data"]
                if isinstance(data, list):
                    return data
            if "blocks" in result:
                return result["blocks"]

        # 格式3: {node: {content: {blocks: [...]}}}
        node = doc.get("node", {})
        if isinstance(node, dict):
            content = node.get("content", {})
            if isinstance(content, dict) and "blocks" in content:
                return content["blocks"]
            if "blocks" in node:
                return node["blocks"]

        # 格式4: {content: {blocks: [...]}}
        content = doc.get("content", {})
        if isinstance(content, dict) and "blocks" in content:
            return content["blocks"]

        # 格式5: 响应体本身就是 content 字段
        for key in ["body", "document", "page"]:
            section = doc.get(key, {})
            if isinstance(section, dict) and "blocks" in section:
                return section["blocks"]

        return []

    def _get_block_text(self, block) -> str:
        """从文档块中提取文本内容"""
        if not isinstance(block, dict):
            return str(block) if block else ""

        # 直接有 text 字段
        if "text" in block:
            text = block["text"]
            if isinstance(text, str):
                return text

        # 按 blockType 提取
        block_type = block.get("blockType", "")
        type_content = block.get(block_type, {})

        if isinstance(type_content, dict):
            text = type_content.get("text", "")
            if isinstance(text, str) and text:
                return text

            # 从 children (inline elements) 中拼接文本
            children = type_content.get("children", [])
            if children:
                parts = []
                for child in children:
                    if isinstance(child, dict):
                        child_text = child.get("text", "")
                        if child_text:
                            parts.append(child_text)
                if parts:
                    return "".join(parts)

        # heading 特殊处理
        heading = block.get("heading", {})
        if isinstance(heading, dict):
            return self._get_block_text({"text": heading.get("text", ""), **heading})

        # paragraph 特殊处理
        paragraph = block.get("paragraph", {})
        if isinstance(paragraph, dict):
            return self._get_block_text({"text": paragraph.get("text", ""), **paragraph})

        return ""

    def _is_interface_name(self, text: str) -> bool:
        """判断文本是否是 WebSocket 接口名称（如 sim.loadModel, simArcs.ahmGetHierarchy）"""
        if not text:
            return False
        text = text.strip()
        # 匹配 xxx.yyy 格式的接口名
        patterns = [
            r"^sim\.",           # sim.loadModel, sim.getObjectPosition
            r"^simArcs\.",       # simArcs.ahmGetHierarchy, simArcs.amStart
            r"^simIK\.",         # simIK.*
            r"^simAssimp\.",     # simAssimp.*
            r"^simStepOrIges\.", # simStepOrIges.*
            r"^wsRemoteApi\.",   # wsRemoteApi.require
        ]
        return any(re.match(p, text) for p in patterns)

    def _add_interface_to_index(self, index: Dict, iface_name: str, content_blocks: list):
        """将一个接口的所有文档块解析并添加到索引"""
        description_parts = []
        params = []

        for block in content_blocks:
            block_type = block.get("blockType", "")

            if block_type == "paragraph":
                text = self._get_block_text(block)
                if text:
                    description_parts.append(text)
            elif block_type == "table":
                table_params = self._parse_table_block(block)
                params.extend(table_params)
            elif block_type in ("unorderedList", "orderedList"):
                text = self._get_block_text(block)
                if text:
                    description_parts.append(f"- {text}")
            elif block_type == "blockquote":
                text = self._get_block_text(block)
                if text:
                    description_parts.append(f"> {text}")

        index["interfaces"][iface_name] = {
            "func": iface_name,
            "description": "\n".join(description_parts),
            "params": params,
            "block_count": len(content_blocks),
        }

    def _parse_table_block(self, block) -> list:
        """解析表格块为参数列表（参数名、类型、必填、说明）"""
        table = block.get("table", {})
        if not table:
            return []

        # 表格可能有 cells 或 rows 字段
        rows = table.get("cells", table.get("rows", []))
        if not rows or len(rows) < 2:
            return []

        # 第一行是表头
        headers = []
        for cell in rows[0]:
            headers.append(self._get_cell_text(cell))

        params = []
        for row in rows[1:]:
            if not row:
                continue
            param = {}
            for i, cell in enumerate(row):
                if i < len(headers) and headers[i]:
                    param[headers[i]] = self._get_cell_text(cell)
            if param:
                params.append(param)

        return params

    def _get_cell_text(self, cell) -> str:
        """从表格单元格提取文本"""
        if isinstance(cell, str):
            return cell
        if isinstance(cell, dict):
            # 可能有 text 字段
            text = cell.get("text", "")
            if text:
                return text
            # 可能有 children (inline elements)
            children = cell.get("children", [])
            if children:
                parts = []
                for child in children:
                    if isinstance(child, dict):
                        parts.append(child.get("text", ""))
                    elif isinstance(child, str):
                        parts.append(child)
                return "".join(parts)
            return ""
        if isinstance(cell, list):
            return "".join(self._get_cell_text(c) for c in cell)
        return str(cell) if cell else ""

    def _extract_text_content(self, doc) -> Optional[str]:
        """从文档响应中提取纯文本内容（兜底方案）"""
        if isinstance(doc, str):
            return doc
        if not isinstance(doc, dict):
            return None

        # 按优先级检查可能的文本字段
        for key in ["text", "content", "markdown", "body", "html"]:
            value = doc.get(key)
            if isinstance(value, str) and len(value) > 50:
                return value
            elif isinstance(value, dict):
                text = self._extract_text_content(value)
                if text:
                    return text
        return None

    def _parse_text_to_index(self, text: str) -> Dict:
        """从纯文本内容解析接口索引（兜底方案）"""
        index = {"interfaces": {}}
        lines = text.split("\n")

        current_iface = None
        current_desc = []

        for line in lines:
            stripped = line.strip()
            if self._is_interface_name(stripped):
                if current_iface:
                    index["interfaces"][current_iface] = {
                        "func": current_iface,
                        "description": "\n".join(current_desc),
                        "params": [],
                    }
                current_iface = stripped
                current_desc = []
            elif current_iface and stripped:
                current_desc.append(stripped)

        if current_iface:
            index["interfaces"][current_iface] = {
                "func": current_iface,
                "description": "\n".join(current_desc),
                "params": [],
            }

        return index
    
    def _load_content_cache(self) -> Dict:
        """加载内容缓存"""
        if self._content_cache:
            return self._content_cache
        
        if self.content_cache_file.exists():
            try:
                with open(self.content_cache_file, "r", encoding="utf-8") as f:
                    self._content_cache = json.load(f)
                return self._content_cache
            except Exception:
                pass
        
        return {}
    
    def _update_content_cache(self, interface_name: str, content: Dict):
        """更新内容缓存"""
        cache = self._load_content_cache()
        cache[interface_name] = {
            "data": content,
            "cached_at": time.time()
        }
        
        with open(self.content_cache_file, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
        
        self._content_cache = cache
    
    def _save_index(self, index: Dict):
        """保存索引到文件"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)
        
        self._index_cache = index
    
    def _mock_dingtalk_response(self) -> Dict:
        """模拟钉钉文档响应（测试用）"""
        return {
            "sheets": [
                {
                    "name": "运动控制",
                    "cells": [
                        {
                            "interface_name": "amStart",
                            "node_id": "node_001",
                            "position": "A10",
                            "method": "POST",
                            "path": "/api/v1/amStart",
                            "params": [
                                {"name": "axis", "type": "string", "required": True},
                                {"name": "speed", "type": "number", "required": False}
                            ],
                            "response": {"status": "success", "data": {}},
                            "description": "启动轴运动"
                        }
                    ]
                }
            ]
        }


# ========== 便捷函数 ==========

def get_skill(cache_ttl_hours: int = 24) -> DingTalkDocClient:
    """获取钉钉文档 Skills 实例"""
    return DingTalkDocClient(ttl_hours=cache_ttl_hours)


def check_cache_status():
    """快速查看缓存状态"""
    skill = get_skill()
    status = skill.get_cache_status()
    
    print("\n📊 钉钉文档缓存状态")
    print("=" * 40)
    print(f"索引文件: {'✅ 存在' if status['index_exists'] else '❌ 不存在'}")
    print(f"内容缓存: {'✅ 存在' if status['content_cache_exists'] else '❌ 不存在'}")
    print(f"接口数量: {status['interfaces_count']}")
    print(f"缓存年龄: {status['cache_age_hours']:.1f} 小时" if status['cache_age_hours'] else "缓存年龄: 未知")
    print(f"TTL 有效期: {status['ttl_hours']} 小时")
    print(f"状态: {'⏰ 已过期' if status['is_expired'] else '✅ 有效'}")
    print("=" * 40)
    
    return status


if __name__ == "__main__":
    # 测试：自动从配置文件加载凭证
    skill = DingTalkDocClient()

    # 查看缓存状态
    check_cache_status()

    # 测试：尝试不同的 API 端点
    print("\n" + "="*60)
    print("测试钉钉 API 连接...")
    print("="*60)

    # 先获取 token
    token = skill._get_access_token()
    if not token:
        print("❌ 无法获取 access_token")
        exit(1)

    headers = {
        "x-acs-dingtalk-access-token": token,
        "Content-Type": "application/json"
    }

    # 尝试 1: 获取知识库列表
    print("\n[尝试 1] 获取知识库列表...")
    url1 = f"{skill.dingtalk_api_base}/v1.0/doc/workspaces"
    params1 = {"operatorId": skill.operator_id}

    try:
        resp = requests.get(url1, headers=headers, params=params1, timeout=10)
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            print("✅ 知识库列表获取成功！")
            data = resp.json()
            print(json.dumps(data, ensure_ascii=False, indent=2)[:800])
        else:
            print(f"❌ 失败: {resp.text}")
    except Exception as e:
        print(f"❌ 异常: {e}")

    # 尝试 2: 直接获取节点
    print("\n[尝试 2] 直接获取节点...")
    doc = skill._fetch_full_document_from_dingtalk()

    if doc:
        print("\n✅ 成功获取文档！")
        print("\n文档结构：")
        print(json.dumps(doc, ensure_ascii=False, indent=2)[:1000])

        # 尝试解析文档
        print("\n[尝试 3] 解析文档为接口索引...")
        index = skill._parse_document_to_index(doc)
        iface_count = len(index.get("interfaces", {}))
        print(f"解析到 {iface_count} 个接口")
        if iface_count > 0:
            for name, meta in index["interfaces"].items():
                print(f"  - {name}: {meta.get('description', '')[:60]}...")
    else:
        print("\n❌ 获取文档失败")
        print("\n建议：")
        print("1. 检查文档 URL 是否正确")
        print("2. 确认文档类型（wiki_doc 可能需要不同的 API）")
        print("3. 查看 raw_api_response.json 了解 API 返回了什么")