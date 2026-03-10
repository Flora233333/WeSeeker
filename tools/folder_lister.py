"""
文件夹内容列举工具
基于 Everything HTTP API 列出指定文件夹的直属子项
"""

import json
import os
from typing import Dict, List, Optional

import requests

from core.config_loader import load_config
from tools.everything_search import _format_timestamp, format_file_size


def list_folder_contents(
    folder_path: str,
    max_results: int = 50,
) -> List[Dict]:
    """列出指定文件夹中的直属子项。"""
    if not folder_path:
        raise Exception("文件夹路径不能为空")

    config = load_config()
    everything_config = config.get("everything", {})

    host = everything_config.get("host", "127.0.0.1")
    port = everything_config.get("port", 8080)

    normalized_path = os.path.normpath(folder_path)
    query = f'parent:"{normalized_path}"'

    url = f"http://{host}:{port}/"
    params = {
        "search": query,
        "json": 1,
        "count": max_results,
        "path_column": 1,
        "size_column": 1,
        "date_modified_column": 1,
        "date_created_column": 1,
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        results_data = data.get("results", [])
        if not results_data and isinstance(data, list):
            results_data = data

        results: List[Dict] = []
        for item in results_data:
            file_name = item.get("name", "")
            dir_path = item.get("path", "")

            if dir_path and file_name:
                full_path = os.path.join(dir_path, file_name)
            elif dir_path:
                full_path = dir_path
                file_name = os.path.basename(dir_path)
            else:
                full_path = file_name

            size_val = item.get("size", 0)
            if isinstance(size_val, str):
                size_val = int(size_val) if size_val.isdigit() else 0

            results.append(
                {
                    "name": file_name,
                    "path": full_path,
                    "size": size_val,
                    "modified": _format_timestamp(item.get("date_modified")),
                    "created": _format_timestamp(item.get("date_created")),
                    "is_dir": item.get("type", "file") == "folder",
                }
            )

        return results[:max_results]

    except requests.exceptions.ConnectionError:
        raise Exception("Everything 服务未启动，请确认 Everything 是否在运行并开启了 HTTP 服务（默认端口 8080）")
    except requests.exceptions.Timeout:
        raise Exception("读取文件夹内容超时，请稍后重试")
    except json.JSONDecodeError:
        raise Exception("Everything 返回数据格式错误，请检查 Everything HTTP 服务配置")
    except Exception as e:
        raise Exception(f"读取文件夹内容出错: {str(e)}")


def format_folder_items(folder_name: str, items: List[Dict], max_display: int = 10) -> str:
    """将文件夹直属子项格式化为用户可读文本。"""
    display_items = items[:max_display]
    lines = [f"文件夹「{folder_name}」里有 {len(items)} 个项目："]

    for idx, item in enumerate(display_items, 1):
        if item.get("is_dir"):
            lines.append(f"{idx}. {item['name']} — 文件夹 — 修改于 {item['modified']}")
        else:
            size_str = format_file_size(item.get("size", 0))
            lines.append(f"{idx}. {item['name']} — {size_str} — 文件 — 修改于 {item['modified']}")

    if len(items) > max_display:
        lines.append(f"\n... 还有 {len(items) - max_display} 个项目未显示")

    lines.append(
        "\n你想看哪个？可以说当前这组结果里的序号；"
        "如果某一项是文件夹，我也可以继续展开。"
        "该序号只对应最近一组结果，不对应更早的列表。"
    )
    return "\n".join(lines)


LIST_FOLDER_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "list_folder_contents",
        "description": "列出指定文件夹中的直属子项（文件和子文件夹）。必须先通过 search_files 找到目标文件夹，再使用 folder_index 从当前候选列表中选择，避免路径错误。",
        "parameters": {
            "type": "object",
            "properties": {
                "folder_index": {
                    "type": "integer",
                    "description": "文件夹序号（必填），必须先通过 search_files 找到目标文件夹后再传入"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最大返回结果数，默认 50",
                    "default": 50
                }
            },
            "required": ["folder_index"]
        }
    }
}
