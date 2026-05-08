"""
Skill 注册表

自动发现 skills/ 包下每个子目录中的 skill.py，注册 BaseFixSkill 子类。
新增 skill 只需加目录（含 SKILL.md + _init_.py），不需要改注册逻辑。

目录结构:
  skills/
    wrong_test_data/
      SKILL.md       ← 元数据 + 正文说明
      skill.py       ← Python 实现
      reference.md   ← 附属关联文档（可选）
"""

import importlib
import logging
import os
from typing import Optional

from .base import BaseFixSkill

logger = logging.getLogger("fix_agent.skills")


class SkillRegistry:
    """
    Skill 注册表（单例）。

    用法:
        registry = SkillRegistry()
        skill = registry.get_skill("wrong_test_data")
        result = skill.execute(state)
    """

    _instance: Optional["SkillRegistry"] = None     # # _instance 可以是 SkillRegistry 对象，也可以是 None。

    def __new__(cls) -> "SkillRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)    # # 创建对象
            cls._instance._skills = {}              # # 初始化字典
            cls._instance._skill_metadata = {}
            cls._instance._discover_skills()        # # 开始扫描注册
        return cls._instance                        


    def _discover_skills(self):
        """
        扫描 skills/ 下的子目录，查找 skill.py 并注册 BaseFixSkill 子类。
        同时读取 SKILL.md 的 frontmatter 元数据。
        """

        skills_dir = os.path.dirname(__file__)      # # 获取当前文件的根目录
        for entry in sorted(os.listdir(skills_dir)): # # 遍历目录下的所有文件和子目录
            entry_path = os.path.join(skills_dir, entry)
            if not os.path.isdir(entry_path):
                continue
            if entry.startswith("_"):
                continue

            skill_file = os.path.join(entry_path, "__init__.py")
            if not os.path.exists(skill_file):
                continue

            full_module = f"fix_agent.skills.{entry}"   # "fix_agent.skills.wrong_test_data"
            try:
                module = importlib.import_module(full_module)  # 等于 import fix_agent.skills.wrong_test_data
            except ImportError as e:
                logger.warning("无法导入 skill 模块 %s: %s", full_module, e)
                continue
            
            # 说白了这段代码就是在__init__.py文件里面找继承了 BaseFixSkill 的那个类
            for attr_name in dir(module):               # 模块里所有变量名
                attr = getattr(module, attr_name)       # 拿到实际对象
                if (
                    isinstance(attr, type)              # 是一个类（不是函数、不是变量）
                    and attr.category                   # 且设置了 category（不为空字符串）
                    and issubclass(attr, BaseFixSkill)  # 继承了 BaseFixSkill
                    and attr is not BaseFixSkill        # 但不是 BaseFixSkill 本身
                ):
                    self._register(attr)                # 注册它！

            # 读取 SKILL.md 元数据
            skill_md = os.path.join(entry_path, "SKILL.md")
            if os.path.exists(skill_md):
                metadata = self._parse_skill_md(skill_md)
                self._skill_metadata[entry] = metadata

        logger.info("已注册 %d 个 skill: %s", len(self._skills), list(self._skills.keys()))


    def _register(self, skill_cls: type[BaseFixSkill]):
        """注册一个 skill 类。"""

        instance = skill_cls()
        if instance.category in self._skills:
            logger.warning("skill category 冲突: %s 已存在，将被 %s 覆盖",
                           instance.category, instance.name)
        self._skills[instance.category] = instance
        logger.debug("注册 skill: category=%s, name=%s, deterministic=%s",
                     instance.category, instance.name, instance.is_deterministic)

######################### 对外展示的方法 #########################

    def get_skill(self, category: str) -> Optional[BaseFixSkill]:
        """根据 error_category 值查找 skill。"""

        return self._skills.get(category)


    def list_skills(self) -> dict[str, BaseFixSkill]:
        """返回所有已注册 skill。"""

        return dict(self._skills)

