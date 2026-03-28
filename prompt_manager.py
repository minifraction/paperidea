#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
提示词管理器 - 管理外部化的 AI 提示词

Copyright (c) 2024 antiproton
License: MIT
"""

from pathlib import Path
from typing import Dict, List

# 尝试导入 Jinja2，如果不存在则使用简单的字符串替换
try:
    from jinja2 import Template
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    print("⚠️ 警告: Jinja2 未安装，将使用简单的字符串替换。建议运行: pip install Jinja2")


class PromptManager:
    """
    提示词管理器
    
    管理外部化的 AI 提示词，支持：
    1. 从文件加载提示词
    2. 变量替换（使用 Jinja2 模板语法）
    
    目录结构:
    prompts/
    ├── extract_structure_system.txt
    ├── extract_structure_user.txt
    ├── generate_ideas_system.txt
    ├── generate_ideas_user.txt
    ├── expand_model_system.txt
    ├── expand_model_user.txt
    ├── infer_methods_system.txt
    ├── infer_methods_user.txt
    └── top_journals.txt
    """
    
    def __init__(self):
        """
        初始化提示词管理器
        """
        self.prompts_dir = Path(__file__).parent / "prompts"
    
    def load_prompt(self, task: str, role: str) -> str:
        """
        加载提示词文件
        
        文件路径: prompts/{task}_{role}.txt
        
        Args:
            task: 任务名称，如 "extract_structure", "generate_ideas"
            role: 角色，"system" 或 "user"
            
        Returns:
            提示词文本
            
        Raises:
            FileNotFoundError: 如果提示词文件不存在
        """
        prompt_file = self.prompts_dir / f"{task}_{role}.txt"
        
        if prompt_file.exists():
            return prompt_file.read_text(encoding='utf-8')
        
        raise FileNotFoundError(
            f"提示词文件不存在: {prompt_file}\n"
            f"请确保 prompts/{task}_{role}.txt 存在"
        )
    
    def render_prompt(self, task: str, variables: Dict[str, any]) -> str:
        """
        渲染提示词（替换变量）
        
        支持 Jinja2 模板语法:
        - {{variable}} - 变量替换
        - {% if condition %}...{% endif %} - 条件判断
        - {% for item in list %}...{% endfor %} - 循环
        
        Args:
            task: 任务名称
            variables: 变量字典
            
        Returns:
            渲染后的提示词文本
        """
        template_text = self.load_prompt(task, "user")
        
        if HAS_JINJA2:
            # 使用 Jinja2 渲染
            template = Template(template_text)
            return template.render(**variables)
        else:
            # 简单的字符串替换（后备方案）
            result = template_text
            for key, value in variables.items():
                placeholder = f"{{{{{key}}}}}"
                result = result.replace(placeholder, str(value) if value is not None else "")
            return result
    
    def get_messages(self, task: str, variables: Dict[str, any]) -> List[Dict[str, str]]:
        """
        获取完整的 messages 列表（用于 API 调用）
        
        Args:
            task: 任务名称
            variables: 变量字典
            
        Returns:
            OpenAI 格式的 messages 列表:
            [
                {"role": "system", "content": "..."},
                {"role": "user", "content": "..."}
            ]
        """
        system_prompt = self.load_prompt(task, "system")
        user_prompt = self.render_prompt(task, variables)
        
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    
    def load_top_journals(self) -> Dict[str, List[str]]:
        """
        加载顶级期刊列表
        
        文件路径: prompts/top_journals.txt
        
        文件格式:
        # 注释
        期刊全称 | 别名1,别名2,...
        
        Returns:
            字典，键为标准化期刊名，值为别名列表（包含全称）
            如果文件不存在，返回空字典
        """
        journal_file = self.prompts_dir / "top_journals.txt"
        
        if not journal_file.exists():
            return {}
        
        journals = {}
        content = journal_file.read_text(encoding='utf-8')
        
        for line in content.strip().split('\n'):
            line = line.strip()
            # 跳过空行和注释行
            if not line or line.startswith('#'):
                continue
            
            # 解析格式: 期刊全称 | 别名1,别名2,...
            if '|' in line:
                parts = line.split('|', 1)
                full_name = parts[0].strip()
                aliases = [a.strip() for a in parts[1].split(',') if a.strip()]
                # 确保全称也在别名列表中（用于匹配）
                if full_name not in aliases:
                    aliases.append(full_name)
                journals[full_name] = aliases
        
        return journals
    
    def match_journal(self, journal_ref: str) -> tuple:
        """
        匹配期刊引用到顶级期刊列表
        
        Args:
            journal_ref: arXiv 返回的期刊引用字符串，如 "Phys. Rev. Lett. 123, 456 (2024)"
            
        Returns:
            (是否匹配, 标准化期刊名)
        """
        if not journal_ref:
            return False, ""
        
        top_journals = self.load_top_journals()
        if not top_journals:
            return False, ""
        
        journal_ref_lower = journal_ref.lower()
        
        for full_name, aliases in top_journals.items():
            for alias in aliases:
                # 不区分大小写的部分匹配
                if alias.lower() in journal_ref_lower:
                    return True, full_name
        
        return False, ""


# 便捷函数
def get_prompt_manager() -> PromptManager:
    """
    获取 PromptManager 实例的便捷函数
    
    Returns:
        PromptManager 实例
    """
    return PromptManager()
