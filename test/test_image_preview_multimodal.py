#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试图片文件预览与多模态摘要链路
"""

import base64
import io
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from PIL import Image

from core.agent import Agent
from core.llm_router import LLMClient
from tools.file_summarizer import build_image_summary_prompt, read_file_content


def _write_temp_png() -> str:
    png_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8"
        "/w8AAgMBgN6cN2QAAAAASUVORK5CYII="
    )
    temp_dir = Path(tempfile.mkdtemp(prefix="weseeker_img_test_"))
    image_path = temp_dir / "sample.png"
    image_path.write_bytes(base64.b64decode(png_base64))
    return str(image_path)


class FakeLLM:
    def __init__(self, summary_text: str):
        self.summary_text = summary_text
        self.messages_seen: List[List[Dict[str, Any]]] = []

    def build_multimodal_user_message(self, text: str, image_paths: list, file_type: str = "image") -> Dict[str, Any]:
        return {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                *[
                    {"type": "image_url", "image_url": {"url": f"mock://{Path(path).name}"}}
                    for path in image_paths
                ],
            ],
        }

    def chat(self, messages: list, tools: Optional[list] = None, tool_choice: str = "auto") -> Dict[str, Any]:
        self.messages_seen.append(messages)
        return {"content": self.summary_text, "tool_calls": None}

    def get_response_content(self, response: Dict[str, Any]) -> Optional[str]:
        return response.get("content")

    def get_tool_calls(self, response: Dict[str, Any]):
        return response.get("tool_calls")


def test_image_preview_result_shape() -> None:
    image_path = _write_temp_png()
    result = read_file_content(image_path, depth="L1")

    assert result["success"] is True
    assert result["file_type"] == "image"
    assert result["content"] is None
    assert result["images"] == [image_path]
    assert result["metadata"]["image_count"] == 1

    print("[PASS] 图片预览结果结构正确")


def test_agent_image_summary_flow() -> None:
    image_path = _write_temp_png()
    result = read_file_content(image_path, depth="L1")

    fake = FakeLLM("这是一张简单图片截图，当前测试链路已经走到多模态摘要分支。")
    agent = Agent(debug=False)
    agent.llm_client = cast(Any, fake)

    rendered = agent._render_preview_response(image_path, result)

    assert "🖼️ 图片摘要" in rendered
    assert "多模态摘要分支" in rendered
    assert fake.messages_seen, "应调用多模态消息摘要"

    multimodal_message = fake.messages_seen[0][1]
    assert multimodal_message["role"] == "user"
    assert isinstance(multimodal_message["content"], list)
    assert multimodal_message["content"][0]["type"] == "text"
    assert multimodal_message["content"][1]["type"] == "image_url"

    print("[PASS] Agent 图片摘要链路正确")


def test_image_summary_prompt() -> None:
    prompt = build_image_summary_prompt(
        "image",
        "sample.png",
        {"image_paths": ["a.png"]},
    )

    assert "sample.png" in prompt
    assert "快速判断" in prompt
    assert "1 张图片" in prompt

    print("[PASS] 图片摘要 prompt 正确")


def test_prepare_image_payload_preserves_aspect_ratio() -> None:
    temp_dir = Path(tempfile.mkdtemp(prefix="weseeker_img_resize_"))
    image_path = temp_dir / "large.jpg"

    Image.new("RGB", (4000, 2000), color=(120, 80, 40)).save(image_path, format="JPEG")

    client = LLMClient(config={"llm": {"provider": "lmstudio", "api_base": "http://localhost:1234"}})
    mime_type, image_bytes = client._prepare_image_payload(str(image_path), max_edge=2048)

    resized = Image.open(io.BytesIO(image_bytes))

    assert mime_type == "image/jpeg"
    assert max(resized.size) <= 2048
    assert resized.size == (2048, 1024)

    print("[PASS] 图片标准化时保持原始长宽比")


def test_multimodal_image_edge_config() -> None:
    client = LLMClient(
        config={
            "llm": {
                "provider": "lmstudio",
                "api_base": "http://localhost:1234",
                "local": {
                    "multimodal": {
                        "image_max_edge": {
                            "image": 2048,
                            "pdf": 3072,
                            "ppt": 3072,
                        }
                    }
                },
            }
        }
    )

    assert client._get_multimodal_image_edge("image") == 2048
    assert client._get_multimodal_image_edge("pdf") == 3072
    assert client._get_multimodal_image_edge("ppt") == 3072

    print("[PASS] 多模态图片缩放配置读取正确")


if __name__ == "__main__":
    test_image_preview_result_shape()
    test_agent_image_summary_flow()
    test_image_summary_prompt()
    test_prepare_image_payload_preserves_aspect_ratio()
    test_multimodal_image_edge_config()
