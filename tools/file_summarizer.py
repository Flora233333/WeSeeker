"""
文件内容摘要
支持 PPT/PDF/Excel/Word/文本等多格式内容提取

注意：本模块只做本地内容提取，不直接调用 LLM。
LLM 总结由调用方（Agent）负责。
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

# 支持的文件类型
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.py', '.js', '.java', '.c', '.cpp', '.h', '.hpp',
                   '.json', '.yaml', '.yml', '.xml', '.html', '.htm', '.css', '.sql',
                   '.log', '.ini', '.conf', '.cfg', '.sh', '.bat', '.ps1', '.csv'}

WORD_EXTENSIONS = {'.docx'}
EXCEL_EXTENSIONS = {'.xlsx', '.xls'}
PPT_EXTENSIONS = {'.pptx'}
PDF_EXTENSIONS = {'.pdf'}


def detect_file_type(file_path: str) -> str:
    """
    检测文件类型

    Returns:
        'text', 'word', 'excel', 'ppt', 'pdf', 'unknown'
    """
    ext = Path(file_path).suffix.lower()

    if ext in TEXT_EXTENSIONS:
        return 'text'
    elif ext in WORD_EXTENSIONS:
        return 'word'
    elif ext in EXCEL_EXTENSIONS:
        return 'excel'
    elif ext in PPT_EXTENSIONS:
        return 'ppt'
    elif ext in PDF_EXTENSIONS:
        return 'pdf'
    else:
        return 'unknown'


def file_summarizer(
    file_path: str,
    depth: str = "L1",
    max_chars: Optional[int] = None,
    max_pages: Optional[int] = None,
    max_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    文件内容预览与摘要

    根据文件类型自动选择预览策略，提取内容并返回结构化结果。
    本函数不直接调用 LLM，仅做本地内容提取。

    Args:
        file_path: 文件完整路径
        depth: 预览深度: "L1"(默认) / "L2"(详细) / "L3"(全量)
        max_chars: 文本类最大读取字符数（覆盖 depth 默认值）
        max_pages: PPT/PDF 最大预览页数（覆盖 depth 默认值）
        max_rows: Excel 最大预览行数（覆盖 depth 默认值）

    Returns:
        字典包含:
        - success: bool - 是否成功
        - file_type: str - 文件类型
        - preview_method: str - 使用的预览方法
        - content: str | None - 提取的文本内容（文本类）
        - images: list[str] | None - 生成的预览图路径列表（PPT/图片类）
        - metadata: dict - 附加元信息
            - total_pages: int - 总页数（PPT/PDF）
            - sheet_names: list - Sheet名列表（Excel）
            - word_count: int - 总字数估算
            - has_more: bool - 是否还有未展示的内容
        - estimated_tokens: int - 本次提取预计消耗的 token 数
        - error: str | None - 错误信息
    """
    if not os.path.exists(file_path):
        return {
            "success": False,
            "file_type": "unknown",
            "preview_method": "none",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"文件不存在: {file_path}"
        }

    # 根据 depth 设置默认参数
    params = _get_depth_params(depth)
    if max_chars is not None:
        params['max_chars'] = max_chars
    if max_pages is not None:
        params['max_pages'] = max_pages
    if max_rows is not None:
        params['max_rows'] = max_rows

    file_type = detect_file_type(file_path)

    try:
        if file_type == 'text':
            result = _extract_text(file_path, params['max_chars'])
        elif file_type == 'word':
            result = _extract_docx(file_path, params['max_chars'])
        elif file_type == 'excel':
            result = _extract_excel(file_path, params['max_rows'])
        elif file_type == 'ppt':
            result = _extract_pptx(file_path, params['max_pages'])
        elif file_type == 'pdf':
            result = _extract_pdf(file_path, params['max_pages'])
        else:
            # 未知文件类型，仅返回元信息
            result = _extract_metadata_only(file_path)

        return result

    except Exception as e:
        return {
            "success": False,
            "file_type": file_type,
            "preview_method": "error",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"预览失败: {str(e)}"
        }


def _get_depth_params(depth: str) -> Dict[str, int]:
    """根据深度等级获取默认参数"""
    depth = depth.upper()
    params = {
        'L1': {'max_chars': 2000, 'max_pages': 3, 'max_rows': 10},
        'L2': {'max_chars': 8000, 'max_pages': 6, 'max_rows': 30},
        'L3': {'max_chars': 50000, 'max_pages': 50, 'max_rows': 1000}
    }
    return params.get(depth, params['L1'])


def _estimate_tokens(text: str) -> int:
    """估算 token 数（粗略估算：中文 1 字 ≈ 1.5 tokens，英文 1 词 ≈ 1.3 tokens）"""
    if not text:
        return 0
    # 简单估算：按字符数乘以系数
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.5)


# ============== 各类文件提取器 ==============

def _extract_text(file_path: str, max_chars: int) -> Dict[str, Any]:
    """
    提取纯文本文件内容

    支持: .txt, .md, .py, .js, .json, .yaml, .csv 等
    """
    try:
        # 尝试多种编码读取
        encodings = ['utf-8', 'gbk', 'gb2312', 'utf-16', 'latin-1']
        content = None
        used_encoding = None

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, errors='ignore') as f:
                    content = f.read(max_chars + 1)  # 多读 1 个字符判断截断
                used_encoding = encoding
                break
            except (UnicodeDecodeError, UnicodeError):
                continue

        if content is None:
            return {
                "success": False,
                "file_type": "text",
                "preview_method": "text_reader",
                "content": None,
                "images": None,
                "metadata": {},
                "estimated_tokens": 0,
                "error": "无法识别文件编码"
            }

        # 判断是否截断
        is_truncated = len(content) > max_chars
        if is_truncated:
            content = content[:max_chars]

        # 获取文件统计信息
        total_chars = 0
        try:
            with open(file_path, 'r', encoding=used_encoding, errors='ignore') as f:
                full_content = f.read()
                total_chars = len(full_content)
        except:
            pass

        return {
            "success": True,
            "file_type": "text",
            "preview_method": "text_reader",
            "content": content,
            "images": None,
            "metadata": {
                "total_chars": total_chars,
                "has_more": is_truncated,
                "encoding": used_encoding
            },
            "estimated_tokens": _estimate_tokens(content),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "file_type": "text",
            "preview_method": "text_reader",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"读取文本文件失败: {str(e)}"
        }


def _extract_docx(file_path: str, max_chars: int) -> Dict[str, Any]:
    """
    提取 Word 文档内容 [接口预留]

    支持: .docx
    TODO: 使用 python-docx 提取标题列表 + 正文前 max_chars 字符
    """
    return {
        "success": False,
        "file_type": "word",
        "preview_method": "docx_reader",
        "content": None,
        "images": None,
        "metadata": {},
        "estimated_tokens": 0,
        "error": "Word 文档预览功能尚未实现"
    }


def _extract_excel(file_path: str, max_rows: int) -> Dict[str, Any]:
    """
    提取 Excel 表格内容 [接口预留]

    支持: .xlsx, .xls
    TODO: 使用 openpyxl 提取 Sheet 名称列表 + 第一个 Sheet 前 max_rows 行
    """
    return {
        "success": False,
        "file_type": "excel",
        "preview_method": "xlsx_reader",
        "content": None,
        "images": None,
        "metadata": {},
        "estimated_tokens": 0,
        "error": "Excel 表格预览功能尚未实现"
    }


def _extract_pptx(file_path: str, max_pages: int) -> Dict[str, Any]:
    """
    提取 PPT 演示文稿内容 [接口预留]

    支持: .pptx
    TODO: 使用 python-pptx 提取幻灯片标题列表 + 前 max_pages 页转为图片
    """
    return {
        "success": False,
        "file_type": "ppt",
        "preview_method": "pptx_previewer",
        "content": None,
        "images": None,
        "metadata": {},
        "estimated_tokens": 0,
        "error": "PPT 预览功能尚未实现"
    }


def _extract_pdf(file_path: str, max_pages: int) -> Dict[str, Any]:
    """
    提取 PDF 文档内容 [接口预留]

    支持: .pdf
    TODO: 使用 PyMuPDF 提取前 max_pages 页文字
    """
    return {
        "success": False,
        "file_type": "pdf",
        "preview_method": "pdf_reader",
        "content": None,
        "images": None,
        "metadata": {},
        "estimated_tokens": 0,
        "error": "PDF 预览功能尚未实现"
    }


def _extract_metadata_only(file_path: str) -> Dict[str, Any]:
    """
    仅提取文件元信息（用于未知文件类型）
    """
    try:
        stat = os.stat(file_path)
        return {
            "success": True,
            "file_type": "unknown",
            "preview_method": "metadata_only",
            "content": None,
            "images": None,
            "metadata": {
                "file_size": stat.st_size,
                "modified_time": stat.st_mtime,
                "has_more": False
            },
            "estimated_tokens": 0,
            "error": f"暂不支持的文件类型: {Path(file_path).suffix}"
        }
    except Exception as e:
        return {
            "success": False,
            "file_type": "unknown",
            "preview_method": "metadata_only",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"读取文件元信息失败: {str(e)}"
        }


# ============== Tool Schema（供 LLM function calling 使用） ==============

PREVIEW_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "file_summarizer",
        "description": "预览文件内容。支持文本文件(.txt/.md/.py/.json等)，Word/Excel/PPT/PDF暂不支持。深度L1=快速预览(约2000字)，L2=详细(约8000字)，L3=完整(需确认)。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件的完整路径"
                },
                "depth": {
                    "type": "string",
                    "description": "预览深度: L1(默认快速预览)/L2(详细)/L3(完整)",
                    "enum": ["L1", "L2", "L3"],
                    "default": "L1"
                }
            },
            "required": ["file_path"]
        }
    }
}
