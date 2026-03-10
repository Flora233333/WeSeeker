"""
Everything 搜索工具
通过 HTTP API 调用 Everything 进行文件搜索
"""

import os
import json
import requests
from typing import Optional, List, Dict
from datetime import datetime
from core.config_loader import load_config


# 默认排除的文件扩展名（无意义的系统文件）
EXCLUDED_EXTENSIONS = {
    '.lnk',      # 快捷方式
    '.tmp',      # 临时文件
    '.temp',     # 临时文件
    '.bak',      # 备份文件
    '.old',      # 旧版本文件
    '.swp',      # vim 交换文件
    '.swo',      # vim 交换文件
}

# 默认排除的文件名模式（完全匹配）
EXCLUDED_FILENAMES = {
    'thumbs.db',      # Windows 缩略图缓存
    'desktop.ini',    # 文件夹配置
    '.ds_store',      # macOS 系统文件
    '~$recycle.bin',  # 回收站
    'folder.jpg',     # 文件夹缩略图
    'albumartsmall.jpg',
    'albumart.jpg',
}

# 默认排除的前缀（如 Office 临时文件 ~$）
EXCLUDED_PREFIXES = (
    '~$',            # Office 临时文件
    '.~',            # 某些编辑器临时文件
    '._',            # macOS 资源分支文件
    '$',
)


def _is_excluded_file(file_name: str) -> bool:
    """
    检查文件是否应该被排除

    Args:
        file_name: 文件名（不含路径）

    Returns:
        True 如果文件应该被排除
    """
    if not file_name:
        return True

    file_name_lower = file_name.lower()
    ext = os.path.splitext(file_name_lower)[1]

    # 检查扩展名
    if ext in EXCLUDED_EXTENSIONS:
        return True

    # 检查文件名（完全匹配）
    if file_name_lower in EXCLUDED_FILENAMES:
        return True

    # 检查前缀
    if file_name_lower.startswith(EXCLUDED_PREFIXES):
        return True

    return False


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
    # 请求更多结果以补偿过滤掉的文件（最多请求 3 倍）
    request_count = min(max_results * 3, 100)
    params = {
        "search": query,
        "json": 1,  # JSON 格式输出
        "count": request_count,  # 结果数量限制（多请求一些用于过滤）
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

            # 过滤无意义的系统文件
            if _is_excluded_file(file_name):
                continue

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

        # 限制返回数量
        return results[:max_results]

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
        # Everything 返回的是 Windows FILETIME:
        # - 以 100 纳秒为单位
        # - 起点是 1601-01-01 00:00:00 UTC
        # Unix 时间戳起点是 1970-01-01 00:00:00 UTC
        # 转换公式: unix = filetime / 10_000_000 - 11644473600
        if isinstance(timestamp, str):
            timestamp = int(timestamp)
        elif not isinstance(timestamp, int):
            timestamp = int(timestamp)

        unix_ts = timestamp / 10_000_000 - 11644473600
        dt = datetime.fromtimestamp(unix_ts)
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
                    "description": (
                        "搜索关键词，可以是文件名的部分内容。"
                        "Everything 搜索规则：空格表示 AND（同时包含多个词），"
                        "例如 '项目 pptx' 会匹配文件名(带后缀)中同时含'项目'与'pptx'的文件。"
                        "关键词应只包含文件名中可能真实出现的词，"
                        "必须去掉自然语言修饰词（如'的''了''上周的''那个''帮我找'）。"
                        "当用户提到文件类型时，转换为真实扩展名："
                        "PPT → pptx, Word/文档 → docx, Excel/表格 → xlsx, PDF → pdf。"
                        "例如用户说'项目PPT' → keyword='项目 pptx'。"
                        "如果用户提到的是一个完整的文件夹名（如'2026文档'），"
                        "将其作为完整关键词传入，不要拆分到 path 参数中。"
                    )
                },
                "path": {
                    "type": "string",
                    "description": (
                        "搜索路径约束（可选）非必需参数。"
                        "仅在用户明确指向系统预设目录时使用：'desktop'/'桌面', 'downloads'/'下载', 'documents'/'文档'，或用户给出的具体磁盘路径（如 'D:\\工作'）。"
                        "注意：当用户说'在XX里'而XX是一个自建文件夹名（如'2026文档''项目资料'）时，"
                        "不要填写 path，应将该文件夹名放入 keyword 中搜索。"
                    )
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认 20，不要超过 50",
                    "default": 20
                }
            },
            "required": ["keyword"]
        }
    }
}
