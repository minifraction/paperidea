#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理模块

Copyright (c) 2024 antiproton
License: MIT
"""

import os
from pathlib import Path


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file=None):
        """
        初始化配置管理器
        
        Args:
            config_file: 配置文件路径，默认为当前目录的 .env
        """
        if config_file is None:
            self.config_file = Path(__file__).parent / ".env"
        else:
            self.config_file = Path(config_file)
    
    def load_config(self):
        """
        加载配置
        
        Returns:
            配置字典
        """
        config = {
            'api_key': '',
            'api_url': '',  # 空字符串表示自动根据模型选择
            'model': 'deepseek-chat',
            'font_scale': 1.0,  # 字体缩放比例
            'domain': 'unspecified'  # 领域选择，默认为未指定/通用
        }
        
        if self.config_file.exists():
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        
                        if key == 'DEEPSEEK_API_KEY':
                            config['api_key'] = value
                        elif key == 'DEEPSEEK_API_URL':
                            config['api_url'] = value
                        elif key == 'DEEPSEEK_MODEL':
                            config['model'] = value
                        elif key == 'FONT_SCALE':
                            try:
                                config['font_scale'] = float(value)
                            except:
                                config['font_scale'] = 1.0
                        elif key == 'DOMAIN':
                            config['domain'] = value
        
        # 如果 api_url 为空，根据模型自动选择
        if not config['api_url']:
            from api_client import MODEL_PRESETS
            preset = MODEL_PRESETS.get(config['model'], {})
            config['api_url'] = preset.get('api_url', 'https://api.deepseek.com/v1')
        
        return config
    
    def save_config(self, api_key, api_url=None, model=None, font_scale=None, domain=None):
        """
        保存配置
        
        Args:
            api_key: DeepSeek API Key
            api_url: API URL，默认为 https://api.deepseek.com/v1
            model: 模型名称，默认为 deepseek-chat
            font_scale: 字体缩放比例，默认为 1.0
            domain: 领域名称，默认为 unspecified
        """
        api_url = api_url or 'https://api.deepseek.com/v1'
        model = model or 'deepseek-chat'
        font_scale = font_scale or 1.0
        domain = domain or 'unspecified'
        
        config_content = f"""# PaperIdea 配置文件
# DeepSeek API 配置
# 获取 API Key: https://platform.deepseek.com/

DEEPSEEK_API_KEY={api_key}
DEEPSEEK_API_URL={api_url}
DEEPSEEK_MODEL={model}
FONT_SCALE={font_scale}
DOMAIN={domain}
"""
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            f.write(config_content)
    
    def is_configured(self):
        """检查是否已配置 API Key"""
        config = self.load_config()
        return bool(config.get('api_key'))
    
    def get_api_key(self):
        """获取 API Key"""
        config = self.load_config()
        return config.get('api_key', '')
    
    def get_api_url(self):
        """获取 API URL"""
        config = self.load_config()
        return config.get('api_url', 'https://api.deepseek.com/v1')
    
    def get_model(self):
        """获取模型名称"""
        config = self.load_config()
        return config.get('model', 'deepseek-chat')
