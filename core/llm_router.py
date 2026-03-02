"""
LLM 客户端封装
支持 OpenAI-compatible API 调用，包括 function calling
"""

import os
import yaml
from openai import OpenAI
from typing import Optional


def load_config() -> dict:
    """加载配置文件"""
    config_path = os.path.join(os.path.dirname(__file__), "..", "config", "settings.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 替换路径中的 {username}
    username = os.environ.get("USERNAME", os.environ.get("USER", "user"))
    if "paths" in config:
        for key, value in config["paths"].items():
            if isinstance(value, str):
                config["paths"][key] = value.replace("{username}", username)

    return config


class LLMClient:
    """LLM 客户端，封装 OpenAI-compatible API 调用"""

    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = load_config()

        self.config = config
        llm_config = config.get("llm", {})

        self.client = OpenAI(
            api_key=llm_config.get("api_key", ""),
            base_url=llm_config.get("api_base", "https://api.openai.com/v1")
        )
        self.model = llm_config.get("model", "qwen-plus")

    def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        tool_choice: str = "auto"
    ) -> dict:
        """
        发送聊天请求

        Args:
            messages: 对话消息列表
            tools: 可用的工具列表
            tool_choice: 工具选择策略 ("auto", "none", 或特定工具)

        Returns:
            API 响应字典
        """
        kwargs = {
            "model": self.model,
            "messages": messages,
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice

        response = self.client.chat.completions.create(**kwargs)
        return response

    def get_response_content(self, response) -> Optional[str]:
        """获取响应文本内容"""
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message.content:
                return message.content
        return None

    def get_tool_calls(self, response) -> Optional[list]:
        """获取工具调用列表"""
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                return message.tool_calls
        return None


def load_system_prompt() -> str:
    """加载系统提示词"""
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts", "system_prompt.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "你是文件管家，帮助用户搜索和发送文件。"