#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI API 客户端 - 支持多厂商模型

Copyright (c) 2024 antiproton
License: MIT
"""

import os
import requests


# 预定义的模型配置
MODEL_PRESETS = {
    # DeepSeek
    "deepseek-chat": {"provider": "DeepSeek", "api_url": "https://api.deepseek.com/v1"},
    "deepseek-reasoner": {"provider": "DeepSeek", "api_url": "https://api.deepseek.com/v1"},
    
    # 豆包 (字节跳动)
    "doubao-pro-32k": {"provider": "豆包", "api_url": "https://ark.cn-beijing.volces.com/api/v3"},
    "doubao-lite-32k": {"provider": "豆包", "api_url": "https://ark.cn-beijing.volces.com/api/v3"},
    "doubao-pro-128k": {"provider": "豆包", "api_url": "https://ark.cn-beijing.volces.com/api/v3"},
    "doubao-lite-128k": {"provider": "豆包", "api_url": "https://ark.cn-beijing.volces.com/api/v3"},
    
    # Kimi (月之暗面)
    "moonshot-v1-8k": {"provider": "Kimi", "api_url": "https://api.moonshot.cn/v1"},
    "moonshot-v1-32k": {"provider": "Kimi", "api_url": "https://api.moonshot.cn/v1"},
    "moonshot-v1-128k": {"provider": "Kimi", "api_url": "https://api.moonshot.cn/v1"},
    
    # GLM (智谱)
    "glm-4": {"provider": "GLM", "api_url": "https://open.bigmodel.cn/api/paas/v4"},
    "glm-4-plus": {"provider": "GLM", "api_url": "https://open.bigmodel.cn/api/paas/v4"},
    "glm-4-flash": {"provider": "GLM", "api_url": "https://open.bigmodel.cn/api/paas/v4"},
    "glm-4-air": {"provider": "GLM", "api_url": "https://open.bigmodel.cn/api/paas/v4"},
    
    # MiniMax
    "abab6.5-chat": {"provider": "MiniMax", "api_url": "https://api.minimax.chat/v1"},
    "abab6.5s-chat": {"provider": "MiniMax", "api_url": "https://api.minimax.chat/v1"},
}


class DeepSeekClient:
    """AI API 客户端 - 支持多厂商模型"""
    
    def __init__(self, api_key=None, api_url=None, model=None):
        """
        初始化客户端
        优先使用传入参数，否则从环境变量读取
        """
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        
        # 根据模型自动确定 API URL
        preset = MODEL_PRESETS.get(self.model, {})
        self.provider = preset.get("provider", "DeepSeek")
        self.api_url = api_url or os.getenv("DEEPSEEK_API_URL") or preset.get("api_url", "https://api.deepseek.com/v1")
    
    def is_configured(self):
        """检查是否已配置 API Key"""
        return bool(self.api_key)
    
    def chat(self, messages, temperature=0.7, max_tokens=4000):
        """
        调用 AI API
        
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}, ...]
            temperature: 温度参数
            max_tokens: 最大 token 数
            
        Returns:
            API 返回的文本内容
            
        Raises:
            Exception: API 调用失败时抛出异常
        """
        if not self.api_key:
            raise ValueError("API Key 未配置")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            raise Exception(f"API 调用失败: {str(e)}")
    
    def test_connection(self):
        """测试 API 连接是否正常"""
        try:
            # 使用简单的测试消息
            test_messages = [{"role": "user", "content": "你好"}]
            
            # 根据厂商调整测试参数
            max_tokens = 10
            
            self.chat(test_messages, max_tokens=max_tokens)
            return True, f"{self.provider} 连接成功"
        except Exception as e:
            # 提供更详细的错误信息
            error_msg = str(e)
            if "401" in error_msg:
                error_msg = "API Key 无效或已过期"
            elif "403" in error_msg:
                error_msg = "无访问权限，请检查模型是否有权限"
            elif "429" in error_msg:
                error_msg = "请求过于频繁，请稍后再试"
            elif "Connection" in error_msg:
                error_msg = "网络连接失败，请检查网络"
            return False, f"{self.provider} 连接失败: {error_msg}"


def get_model_list():
    """获取支持的模型列表"""
    return list(MODEL_PRESETS.keys())


def get_model_info(model_name):
    """获取模型信息"""
    return MODEL_PRESETS.get(model_name, {"provider": "未知", "api_url": ""})
