"""
LLM 客户端封装
支持 OpenAI-compatible API 调用，包括 function calling
支持云端和本地 LLM（LM Studio / Ollama）
"""

import os
import re
import base64
import io
import mimetypes
from typing import Any, List, Tuple
from openai import OpenAI
from typing import Optional
from PIL import Image, ImageOps
from core.config_loader import load_config

# 本地 LLM 提供商列表
LOCAL_PROVIDERS = ("lmstudio", "ollama")

# 各提供商默认地址
DEFAULT_BASE_URLS = {
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "openai": "https://api.openai.com/v1",
    "lmstudio": "http://localhost:1234/v1",
    "ollama": "http://localhost:11434/v1",
}

DEFAULT_MULTIMODAL_IMAGE_EDGES = {
    "image": 2048,
    "pdf": 3072,
    "ppt": 3072,
}


def _normalize_provider(provider: str) -> str:
    """
    规范化 provider 值

    只支持三种：
    - lmstudio: LM Studio 本地部署
    - ollama: Ollama 本地部署
    - cloud: 云端 API（包括 dashscope、openai、deepseek 等）

    如果填写其他值，默认为 cloud
    """
    provider = provider.lower().strip() if provider else "cloud"

    if provider in ("lmstudio", "ollama"):
        return provider

    # 其他所有值都当作云端处理
    return "cloud"


def _strip_think_blocks(text: str) -> str:
    if not text:
        return text

    cleaned = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return cleaned.strip()


class LLMClient:
    """LLM 客户端，封装 OpenAI-compatible API 调用"""

    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = load_config()

        self.config = config
        llm_config = config.get("llm", {})

        # 获取 provider（必须显式配置，不再自动检测）
        # 只支持三种：lmstudio / ollama / cloud
        provider = llm_config.get("provider", "")
        self.provider = _normalize_provider(provider)

        # 获取 api_key 和 base_url
        api_key = llm_config.get("api_key", "")
        base_url = llm_config.get("api_base", "")

        # 本地 LLM 特殊处理
        if self.provider in LOCAL_PROVIDERS:
            # 本地 LLM 不需要 api_key，使用占位符
            if not api_key:
                api_key = "not-needed"
            # 如果没有设置 base_url，使用默认地址
            if not base_url:
                if self.provider == "ollama":
                    base_url = DEFAULT_BASE_URLS["ollama"]
                else:
                    base_url = DEFAULT_BASE_URLS["lmstudio"]
            else:
                # 用户提供了 base_url，检查是否需要补全 /v1
                # LM Studio 和 Ollama 等本地服务通常需要 /v1 路径
                if not base_url.rstrip("/").endswith("/v1"):
                    base_url = base_url.rstrip("/") + "/v1"

        # 云端 LLM 但没有 base_url，使用默认值
        elif not base_url:
            base_url = DEFAULT_BASE_URLS.get(self.provider, DEFAULT_BASE_URLS["dashscope"])

        # 获取本地 LLM 专用配置
        local_config = llm_config.get("local", {})
        timeout = local_config.get("timeout", 30)

        # 本地 LLM 响应较慢，增加默认超时
        if self.provider in LOCAL_PROVIDERS and timeout < 60:
            timeout = 60

        # 初始化 OpenAI 客户端
        self.client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout
        )

        # 获取模型名称：云端必须配置，本地可选
        model = llm_config.get("model", "")
        if self.provider not in LOCAL_PROVIDERS and not model:
            raise ValueError(
                "配置错误：云端 LLM 必须在 settings.yaml 中设置 llm.model\n"
                "例如：qwen3.5-plus, gpt-4, deepseek-chat 等"
            )
        self.model = model

        # 打印当前使用的提供商（调试用）
        print(f"[LLM] 使用提供商: {self.provider}, 模型: {self.model}")
        if self.provider in LOCAL_PROVIDERS:
            print(f"[LLM] 本地 API 地址: {base_url}")

    def chat(
        self,
        messages: list,
        tools: Optional[list] = None,
        tool_choice: str = "auto"
    ) -> Any:
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

        # 本地 LLM 可能不支持某些参数，根据提供商调整
        if self.provider in LOCAL_PROVIDERS:
            # 某些本地 LLM 不支持 tool_choice 参数
            if "tool_choice" in kwargs:
                del kwargs["tool_choice"]

        try:
            response = self.client.chat.completions.create(**kwargs) # 这一步同时做了构造消息+发送，response就是LLM返回的消息，包括模型返回的文本内容，tool call，以及一些元信息
            return response
        except Exception as e:
            # 添加更友好的错误提示
            if self.provider in LOCAL_PROVIDERS and "connection" in str(e).lower():
                raise Exception(
                    f"无法连接到本地 LLM 服务 ({self.provider})。\n"
                    f"请确认:\n"
                    f"1. {self.provider} 是否已启动\n"
                    f"2. API 地址是否正确 (当前: {self.client.base_url})\n"
                    f"3. 模型是否已加载"
                ) from e
            raise # 这里两个raise是先试着调用接口。
                  # 如果报错了，并且像是本地模型连不上如"and "connection" in str(e)"，那我就换一句人能看懂的话报出来。
                  # 否则我不乱改，直接把原始错误继续抛出去

    def get_response_content(self, response) -> Optional[str]:
        """获取响应文本内容"""
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if message.content:
                return _strip_think_blocks(message.content)
        return None

    def get_tool_calls(self, response) -> Optional[list]:
        """获取工具调用列表"""
        if response.choices and len(response.choices) > 0:
            message = response.choices[0].message
            if hasattr(message, "tool_calls") and message.tool_calls:
                return message.tool_calls
        return None

    def _get_multimodal_image_edge(self, file_type: str = "image") -> int:
        multimodal_config = self.config.get("llm", {}).get("local", {}).get("multimodal", {})
        image_max_edge = multimodal_config.get("image_max_edge", {})

        configured_value = image_max_edge.get(file_type)
        if isinstance(configured_value, int) and configured_value > 0:
            return configured_value

        return DEFAULT_MULTIMODAL_IMAGE_EDGES.get(file_type, DEFAULT_MULTIMODAL_IMAGE_EDGES["image"])

    def encode_image_to_data_url(self, image_path: str, file_type: str = "image") -> str:
        """将本地图片标准化后编码为 data URL，供多模态模型使用。"""
        mime_type, image_bytes = self._prepare_image_payload(
            image_path,
            max_edge=self._get_multimodal_image_edge(file_type),
        )
        encoded = base64.b64encode(image_bytes).decode("ascii")

        return f"data:{mime_type};base64,{encoded}"

    def _prepare_image_payload(self, image_path: str, max_edge: int) -> Tuple[str, bytes]:
        """将本地图片转为模型更容易处理的标准单帧图片，并在必要时等比例缩放。"""
        with Image.open(image_path) as image:
            source_format = (image.format or "").upper()
            image = ImageOps.exif_transpose(image)

            if getattr(image, "is_animated", False):
                image.seek(0)

            has_alpha = "A" in image.getbands()
            prefer_png = has_alpha or source_format == "MPO"
            output_format = "PNG" if prefer_png else "JPEG"
            mime_type = "image/png" if prefer_png else "image/jpeg"

            if output_format == "JPEG":
                image = image.convert("RGB")
            else:
                image = image.convert("RGBA")

            if max(image.size) > max_edge:
                image.thumbnail(
                    (max_edge, max_edge),
                    Image.Resampling.LANCZOS,
                )

            buffer = io.BytesIO()
            save_kwargs: dict[str, Any] = {"format": output_format}
            if output_format == "JPEG":
                save_kwargs["quality"] = 90
                save_kwargs["optimize"] = True
            else:
                save_kwargs["optimize"] = True

            image.save(buffer, **save_kwargs)

        image_bytes = buffer.getvalue()
        if not image_bytes:
            raise ValueError(f"图片编码失败: {image_path}")

        return mime_type, image_bytes

    def build_multimodal_user_message(self, text: str, image_paths: List[str], file_type: str = "image") -> dict:
        """构造 OpenAI-compatible 多模态 user message。"""
        content: list[Any] = [{"type": "text", "text": text}]

        for image_path in image_paths:
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": self.encode_image_to_data_url(image_path, file_type=file_type)},
                }
            )

        return {
            "role": "user",
            "content": content,
        }


def load_system_prompt() -> str:
    """加载系统提示词"""
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "config", "prompts", "system_prompt_2.md")
    if os.path.exists(prompt_path):
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()
    return "你是文件管家，帮助用户搜索和发送文件。"
