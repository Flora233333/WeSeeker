"""
Everything 搜索工具
通过 HTTP API 调用 Everything 进行文件搜索
"""

import os
import json
import requests
from typing import Optional, List, Dict
from datetime import datetime


def load_config() -> dict:
    """加载配置文件"""
    import yaml
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


def search_files(
    keyword: str,
    path: Optional[str] = None,
    max_results: int = 20
) -> List[Dict]:
    """
    使用 Everything 搜索文件

    Args:
        keyword: 搜索关键词
        path: 搜索路径约束（可选）
        max_results: 最大返回结果数

    Returns:
        文件信息列表，每个元素包含：
        - name: 文件名
        - path: 完整路径
        - size: 文件大小（字节）
        - modified: 修改时间
        - created: 创建时间
    """
    config = load_config()
    everything_config = config.get("everything", {})

    host = everything_config.get("host", "127.0.0.1")
    port = everything_config.get("port", 8080)

    # 构建搜索查询
    query = keyword

    # 添加路径约束
    if path:
        # 映射路径别名
        paths_config = config.get("paths", {})
        if path.lower() in ["desktop", "桌面"]:
            path = paths_config.get("desktop", "")
        elif path.lower() in ["downloads", "下载"]:
            path = paths_config.get("downloads", "")
        elif path.lower() in ["documents", "文档"]:
            path = paths_config.get("documents", "")

        if path:
            query = f'"{path}" {query}'

    # 调用 Everything HTTP API
    # Everything HTTP API: http://localhost:8080/?search=keyword&json=1&count=20
    url = f"http://{host}:{port}/"
    params = {
        "search": query,
        "json": 1,  # JSON 格式输出
        "count": max_results,  # 结果数量限制
        "path_column": 1,  # 包含路径列
        "size_column": 1,  # 包含大小列
        "date_modified_column": 1,  # 包含修改时间列
        "date_created_column": 1,  # 包含创建时间列
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results = []
        # Everything HTTP API 返回格式：
        # {"results": [{"type": "file", "name": "xxx", "path": "xxx", "size": 123, ...}]}
        results_data = data.get("results", [])
        if not results_data:
            # 尝试另一种格式（旧版 API 可能直接是列表）
            if isinstance(data, list):
                results_data = data

        for item in results_data:
            # 解析 Everything 返回的结果
            # path 是目录，name 是文件名，需要拼接
            file_name = item.get("name", "")
            dir_path = item.get("path", "")

            # 拼接完整路径
            if dir_path and file_name:
                full_path = os.path.join(dir_path, file_name)
            elif dir_path:
                full_path = dir_path
                file_name = os.path.basename(dir_path)
            else:
                full_path = file_name

            # size 可能是字符串或整数
            size_val = item.get("size", 0)
            if isinstance(size_val, str):
                size_val = int(size_val) if size_val.isdigit() else 0

            file_info = {
                "name": file_name,
                "path": full_path,
                "size": size_val,
                "modified": _format_timestamp(item.get("date_modified")),
                "created": _format_timestamp(item.get("date_created")),
                "is_dir": item.get("type", "file") == "folder"
            }
            results.append(file_info)

        return results

    except requests.exceptions.ConnectionError:
        raise Exception("Everything 服务未启动，请确认 Everything 是否在运行并开启了 HTTP 服务（默认端口 8080）")
    except requests.exceptions.Timeout:
        raise Exception("搜索超时，请稍后重试")
    except json.JSONDecodeError:
        raise Exception("Everything 返回数据格式错误，请检查 Everything HTTP 服务配置")
    except Exception as e:
        raise Exception(f"搜索出错: {str(e)}")


def _format_timestamp(timestamp: Optional[int]) -> str:
    """格式化时间戳"""
    if not timestamp:
        return "未知"

    try:
        # Everything 返回的是 Windows FILETIME (100纳秒单位，从 1601-01-01 开始)
        # 转换为 Unix 时间戳
        dt = datetime.fromtimestamp(timestamp)
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return "未知"


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


# Tool 函数签名（供 LLM function calling 使用）
SEARCH_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_files",
        "description": "搜索本地文件。使用 Everything 进行毫秒级文件搜索。支持关键词、路径约束。",
        "parameters": {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，可以是文件名的部分内容"
                },
                "path": {
                    "type": "string",
                    "description": "搜索路径约束（可选）。可以是 'desktop'/'桌面', 'downloads'/'下载', 'documents'/'文档'，或具体路径"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认 20",
                    "default": 20
                }
            },
            "required": ["keyword"]
        }
    }
}