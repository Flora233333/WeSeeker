"""
文件发送工具
MVP 阶段：Mock 实现，仅打印日志
"""

import os
from typing import Optional


def send_file(file_path: str, target: Optional[str] = None) -> dict:
    """
    发送文件到微信（MVP 阶段为 Mock 实现）

    Args:
        file_path: 文件完整路径
        target: 发送目标（可选，默认为文件传输助手）

    Returns:
        发送结果字典
    """
    # 验证文件是否存在
    if not os.path.exists(file_path):
        return {
            "success": False,
            "error": f"文件不存在: {file_path}"
        }

    # 获取文件信息
    file_name = os.path.basename(file_path)
    file_size = os.path.getsize(file_path)

    # 检查文件大小（微信限制 100MB）
    max_size = 100 * 1024 * 1024  # 100MB
    if file_size > max_size:
        size_mb = file_size / (1024 * 1024)
        return {
            "success": False,
            "error": f"文件过大 ({size_mb:.1f} MB)，超过微信 100MB 限制"
        }

    # MVP 阶段：Mock 发送，打印日志
    target_name = target or "文件传输助手"

    # 格式化文件大小
    if file_size < 1024:
        size_str = f"{file_size} B"
    elif file_size < 1024 * 1024:
        size_str = f"{file_size / 1024:.1f} KB"
    else:
        size_str = f"{file_size / (1024 * 1024):.1f} MB"

    # 打印发送日志（Mock）
    print(f"\n{'='*50}")
    print(f"[MOCK] 发送文件到微信")
    print(f"  目标: {target_name}")
    print(f"  文件: {file_name}")
    print(f"  大小: {size_str}")
    print(f"  路径: {file_path}")
    print(f"{'='*50}\n")

    return {
        "success": True,
        "file_name": file_name,
        "file_size": file_size,
        "target": target_name,
        "message": f"[OK] 文件已发送到「{target_name}」"
    }


# Tool 函数签名（供 LLM function calling 使用）
SEND_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "send_file",
        "description": "发送文件到用户微信。发送前必须经过用户确认。文件会发送到微信「文件传输助手」或指定联系人。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "要发送的文件的完整路径"
                },
                "target": {
                    "type": "string",
                    "description": "发送目标（可选），默认为「文件传输助手」"
                }
            },
            "required": ["file_path"]
        }
    }
}