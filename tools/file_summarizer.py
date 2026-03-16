"""
文件内容摘要
支持 PPT/PDF/Excel/Word/文本等多格式内容提取

注意：本模块只做本地内容提取与总结 Prompt 组装，不直接调用 LLM。
LLM 调用仍由调用方（Agent）负责。
"""

import os
import re
import textwrap
import tempfile
from datetime import date, datetime, time
from typing import Optional, Dict, Any, Tuple
from pathlib import Path

import fitz

from core.config_loader import load_config

# 支持的文件类型
TEXT_EXTENSIONS = {'.txt', '.md', '.markdown', '.py', '.js', '.java', '.c', '.cpp', '.h', '.hpp',
                   '.json', '.yaml', '.yml', '.xml', '.html', '.htm', '.css', '.sql',
                   '.log', '.ini', '.conf', '.cfg', '.sh', '.bat', '.ps1', '.csv'}

WORD_EXTENSIONS = {'.docx'}
EXCEL_EXTENSIONS = {'.xlsx', '.xls'}
PPT_EXTENSIONS = {'.pptx'}
PDF_EXTENSIONS = {'.pdf'}
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.gif'}


def get_summary_system_prompt() -> str:
    return (
        "你是文件管家助手，用户让你预览一个文件。"
        "你的总结目标是：让用户不打开文件也能快速判断这是不是自己要找的那个文件。"
        "语气简洁自然，像管家在口头汇报，不要用'本文档''综上所述'等书面套话。"
        "纯文本输出，不要使用 Markdown 格式标记。"
    )


def build_summary_prompt(content: str, file_type: str, file_name: str) -> str:
    file_type_desc = {
        'text': '文本文件',
        'word': 'Word 文档',
        'excel': 'Excel 表格',
        'ppt': 'PPT 演示文稿',
        'pdf': 'PDF 文档'
    }.get(file_type, '文件')

    # 根据文件类型给出差异化的总结侧重点
    type_hint = {
        'text': '关注文本的主题和关键信息。如果是代码或配置文件，说明其功能和用途。',
        'word': '关注文档的主题、结构大纲和核心结论。如果有标题层级，体现文档的组织结构。',
        'excel': '关注表格的数据主题、包含哪些字段/维度、数据量级和关键数值。',
        'ppt': '关注演示文稿的主题、核心观点和逻辑线索。',
        'pdf': '关注文档的主题、核心内容和关键结论。',
    }.get(file_type, '关注文件的主要内容和用途。')

    max_content_chars = 3000
    is_truncated = len(content) > max_content_chars
    display_content = content[:max_content_chars]

    truncation_notice = (
        "\n（注意：以上为文件的前半部分内容，后续已截断。请基于可见部分总结，不要猜测未展示的内容。）"
        if is_truncated else ""
    )

    # return f"""请对以下{file_type_desc}「{file_name}」进行总结。
    #         总结要求：
    #         - 先用一句话概括这个文件是什么、关于什么主题
    #         - 再用 1-3 句话提炼关键内容
    #         - {type_hint}
    #         - 总结控制在 200-300 字以内
    #         文件内容：
    #         ---
    #         {display_content}
    #         ---{truncation_notice}
    #         总结："""

    return textwrap.dedent(f"""\
        请对以下{file_type_desc}「{file_name}」进行总结。
        总结要求：
        - 先用一句话概括这个文件是什么、关于什么主题
        - 再用 4-5 句话提炼关键内容
        - {type_hint}
        - 总结控制在 200-300 字以内
        文件内容：
        ---
        {display_content}
        ---{truncation_notice}
        总结：""")


def build_image_summary_prompt(file_type: str, file_name: str, metadata: Dict[str, Any]) -> str:
    file_type_desc = {
        'image': '图片',
        'pdf': 'PDF 页面截图',
        'ppt': '演示文稿截图',
    }.get(file_type, '图片文件')

    detail_hints = {
        'image': (
            '先判断图片类型（如照片、截图、扫描件、表格、聊天记录、证书、海报、流程图等），'
            '再根据类型侧重描述：照片说明场景和主体，截图说明来源软件和内容，'
            '表格/文档说明主题和关键字段。'
        ),
        'pdf': (
            '把这些当作 PDF 的逐页截图来理解整份文档。'
            '关注文档主题、章节结构、核心结论或关键数据，'
            '如果有表格或图表，概括其反映的信息而非逐项转写。'
        ),
        'ppt': (
            '把这些当作演示文稿的逐页截图来理解整份 PPT。'
            '关注演示主题、逻辑线索和核心观点，'
            '重点提炼标题页的主题、内容页的关键论点和数据页的核心结论。'
        ),
    }.get(file_type, '判断图片内容类型和主要信息。')

    image_count = len(metadata.get('image_paths') or [])

    return (
        f"请根据提供的{file_type_desc}内容，对文件「{file_name}」做一个简短总结。\n"
        "总结要求：\n"
        "- 先用一句话说明这份文件大概是什么\n"
        "- 再提炼 4-5 条最关键的信息\n"
        f"- {detail_hints}\n"
        "- 如果能看清文字，可提取一定的关键标题/字段，但不要为了逐字转写牺牲概括性\n"
        "- 目标是帮助用户快速判断这是不是自己要找的文件\n"
        f"- 当前共提供 {image_count} 张图片\n"
        "- 纯文本输出，不要使用 Markdown 标记"
    )


def detect_file_type(file_path: str) -> str:
    """
    检测文件类型

    Returns:
        'text', 'word', 'excel', 'ppt', 'pdf', 'image', 'unknown'
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
    elif ext in IMAGE_EXTENSIONS:
        return 'image'
    else:
        return 'unknown'


def read_file_content(
    file_path: str,
    depth: str = "L1",
    max_chars: Optional[int] = None,
    max_pages: Optional[int] = None,
    max_rows: Optional[int] = None
) -> Dict[str, Any]:
    """
    读取文件内容

    根据文件类型自动选择读取策略，提取内容并返回结构化结果。
    本函数不直接调用 LLM，仅做本地内容提取。

    Args:
        file_path: 文件完整路径
        depth: 读取深度: "L1"(默认) / "L2"(详细) / "L3"(全量)
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
        elif file_type == 'image':
            result = _extract_image(file_path)
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
    text_depth_chars = _get_text_depth_chars()
    excel_depth_rows = _get_excel_depth_rows()
    pdf_depth_pages = _get_pdf_depth_pages()
    params = {
        'L1': {'max_chars': text_depth_chars['L1'], 'max_pages': pdf_depth_pages['L1'], 'max_rows': excel_depth_rows['L1']},
        'L2': {'max_chars': text_depth_chars['L2'], 'max_pages': pdf_depth_pages['L2'], 'max_rows': excel_depth_rows['L2']},
        'L3': {'max_chars': text_depth_chars['L3'], 'max_pages': pdf_depth_pages['L3'], 'max_rows': excel_depth_rows['L3']}
    }
    return params.get(depth, params['L1'])


def _get_text_depth_chars() -> Dict[str, int]:
    defaults = {'L1': 2000, 'L2': 5000, 'L3': 8000}
    return _read_depth_config('text', 'depth_chars', defaults)


def _get_excel_depth_rows() -> Dict[str, int]:
    defaults = {'L1': 10, 'L2': 50, 'L3': 100}
    return _read_depth_config('excel', 'depth_rows', defaults)


def _get_pdf_depth_pages() -> Dict[str, int]:
    defaults = {'L1': 1, 'L2': 2, 'L3': 3}

    return _read_depth_config('pdf', 'depth_pages', defaults)


def _read_depth_config(section: str, key: str, defaults: Dict[str, int]) -> Dict[str, int]:
    result = dict(defaults)

    try:
        config = load_config()
        configured = config.get('preview', {}).get(section, {}).get(key, {})
        for level, fallback in defaults.items():
            value = configured.get(level, fallback)
            result[level] = value if isinstance(value, int) and value > 0 else fallback
        return result
    except Exception:
        return dict(defaults)


def _get_pdf_render_scale() -> float:
    try:
        config = load_config()
        value = config.get('preview', {}).get('pdf', {}).get('render_scale', 2.0)
        return float(value) if float(value) > 0 else 2.0
    except Exception:
        return 2.0


def _estimate_tokens(text: str) -> int:
    """估算 token 数（粗略估算：中文 1 字 ≈ 1.5 tokens，英文 1 词 ≈ 1.3 tokens）"""
    if not text:
        return 0
    # 简单估算：按字符数乘以系数
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    other_chars = len(text) - chinese_chars
    return int(chinese_chars * 1.5 + other_chars * 0.5)


def _truncate_preview_content(content: str, max_chars: int) -> Tuple[str, bool]:
    if len(content) <= max_chars:
        return content, False
    return content[:max_chars], True


def _build_text_preview_result(
    file_type: str,
    preview_method: str,
    content: str,
    has_more: bool,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    metadata = {
        "preview_chars": len(content),
        "has_more": has_more,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return {
        "success": True,
        "file_type": file_type,
        "preview_method": preview_method,
        "content": content,
        "images": None,
        "metadata": metadata,
        "estimated_tokens": _estimate_tokens(content),
        "error": None,
    }


def _build_preview_error_result(
    file_type: str,
    preview_method: str,
    error: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "success": False,
        "file_type": file_type,
        "preview_method": preview_method,
        "content": None,
        "images": None,
        "metadata": metadata or {},
        "estimated_tokens": 0,
        "error": error,
    }


def _clean_inline_whitespace(text: str) -> str:
    text = text.replace("\r", " ").replace("\n", " ").replace("\t", " ")
    return re.sub(r"\s+", " ", text).strip()


def _normalize_excel_cell(value: Any, max_length: int = 120) -> str:
    if value is None:
        return ""

    if isinstance(value, datetime):
        if value.time() == time(0, 0, 0):
            text = value.strftime("%Y-%m-%d")
        else:
            text = value.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(value, date):
        text = value.strftime("%Y-%m-%d")
    elif isinstance(value, time):
        text = value.strftime("%H:%M:%S")
    else:
        text = str(value)

    text = _clean_inline_whitespace(text)
    if len(text) > max_length:
        text = text[: max_length - 3].rstrip() + "..."
    return text


def _is_effective_excel_row(cells: list[str]) -> bool:
    return any(cell for cell in cells)


def _select_first_non_empty_sheet(workbook, max_rows: int):
    scan_limit = max(max_rows * 3, 30)

    for sheet_name in workbook.sheetnames:
        worksheet = workbook[sheet_name]
        for row_index, row in enumerate(worksheet.iter_rows(values_only=True), start=1):
            if row_index > scan_limit:
                break
            normalized_cells = [_normalize_excel_cell(cell) for cell in row]
            if _is_effective_excel_row(normalized_cells):
                return worksheet

    return None


def _collect_sheet_preview_rows(worksheet, max_rows: int) -> Tuple[list[list[str]], bool]:
    preview_rows = []

    for row in worksheet.iter_rows(values_only=True):
        normalized_cells = [_normalize_excel_cell(cell) for cell in row]
        if not _is_effective_excel_row(normalized_cells):
            continue

        trimmed_cells = list(normalized_cells)
        while trimmed_cells and not trimmed_cells[-1]:
            trimmed_cells.pop()

        preview_rows.append(trimmed_cells)
        if len(preview_rows) > max_rows:
            return _drop_empty_excel_columns(preview_rows[:max_rows]), True

    return _drop_empty_excel_columns(preview_rows), False


def _drop_empty_excel_columns(rows: list[list[str]]) -> list[list[str]]:
    if not rows:
        return rows

    max_columns = max(len(row) for row in rows)
    keep_indices = []

    for column_index in range(max_columns):
        if any(column_index < len(row) and row[column_index] for row in rows):
            keep_indices.append(column_index)

    if not keep_indices:
        return rows

    cleaned_rows = []
    for row in rows:
        cleaned_rows.append([
            row[column_index] if column_index < len(row) else ""
            for column_index in keep_indices
        ])

    return cleaned_rows


def _format_excel_preview_text(
    file_name: str,
    sheet_names: list[str],
    preview_sheet_name: str,
    preview_rows: list[list[str]],
) -> str:
    lines = [
        f"工作簿: {file_name}",
        f"Sheet 列表: {', '.join(sheet_names)}",
        f"当前预览 Sheet: {preview_sheet_name}",
        "",
    ]

    for row_index, row_cells in enumerate(preview_rows, start=1):
        display_cells = [cell if cell else "[空]" for cell in row_cells]
        line = " | ".join(display_cells)
        if row_index == 1:
            lines.append("表头候选:")
            lines.append(line)
        else:
            lines.append(f"第 {row_index} 行:")
            lines.append(line)
        lines.append("")

    return "\n".join(lines).strip()

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

        content, is_truncated = _truncate_preview_content(content, max_chars)

        return _build_text_preview_result(
            file_type="text",
            preview_method="text_reader",
            content=content,
            has_more=is_truncated,
            extra_metadata={"encoding": used_encoding},
        )

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
    提取 Word 文档纯文字内容

    支持: .docx
    当前仅提取段落中的纯文字，不处理图片、文本框、页眉页脚等复杂对象。
    """
    try:
        from docx import Document
    except ImportError:
        return {
            "success": False,
            "file_type": "word",
            "preview_method": "docx_reader",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": "缺少 python-docx 依赖，暂时无法预览 Word 文档",
        }

    try:
        document = Document(file_path)
        paragraph_texts = []
        non_empty_paragraphs = 0

        for paragraph in document.paragraphs:
            text = paragraph.text.strip()
            if not text:
                continue
            paragraph_texts.append(text)
            non_empty_paragraphs += 1

        if not paragraph_texts:
            return {
                "success": False,
                "file_type": "word",
                "preview_method": "docx_reader",
                "content": None,
                "images": None,
                "metadata": {
                    "paragraph_count": 0,
                },
                "estimated_tokens": 0,
                "error": "Word 文档中未提取到可预览的正文文字，可能是空白文档或主要由图片组成",
            }

        full_content = "\n\n".join(paragraph_texts)
        content, is_truncated = _truncate_preview_content(full_content, max_chars)

        return _build_text_preview_result(
            file_type="word",
            preview_method="docx_reader",
            content=content,
            has_more=is_truncated,
            extra_metadata={
                "paragraph_count": non_empty_paragraphs,
            },
        )
    except Exception as e:
        return {
            "success": False,
            "file_type": "word",
            "preview_method": "docx_reader",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"读取 Word 文档失败: {str(e)}",
        }


def _extract_excel(file_path: str, max_rows: int) -> Dict[str, Any]:
    """
    提取 Excel 表格内容

    当前仅支持 .xlsx，选择第一个非空 Sheet，提取前 max_rows 条非空行。
    """
    suffix = Path(file_path).suffix.lower()
    if suffix == ".xls":
        return _build_preview_error_result(
            file_type="excel",
            preview_method="xlsx_reader",
            error="当前仅支持 .xlsx 预览，.xls 暂未实现",
        )

    try:
        from openpyxl import load_workbook
    except ImportError:
        return _build_preview_error_result(
            file_type="excel",
            preview_method="xlsx_reader",
            error="缺少 openpyxl 依赖，暂时无法预览 Excel 表格",
        )

    try:
        workbook = load_workbook(file_path, read_only=True, data_only=True)
        sheet_names = list(workbook.sheetnames)
        preview_sheet = _select_first_non_empty_sheet(workbook, max_rows)

        if preview_sheet is None:
            return _build_preview_error_result(
                file_type="excel",
                preview_method="xlsx_reader",
                error="Excel 中未提取到可预览的非空表格内容，可能是空表或仅包含样式/图表对象",
                metadata={
                    "sheet_names": sheet_names,
                    "sheet_count": len(sheet_names),
                },
            )

        preview_rows, has_more = _collect_sheet_preview_rows(preview_sheet, max_rows)
        if not preview_rows:
            return _build_preview_error_result(
                file_type="excel",
                preview_method="xlsx_reader",
                error="Excel 中未提取到可预览的非空表格内容，可能是空表或仅包含样式/图表对象",
                metadata={
                    "sheet_names": sheet_names,
                    "sheet_count": len(sheet_names),
                    "preview_sheet": preview_sheet.title,
                },
            )

        preview_text = _format_excel_preview_text(
            file_name=os.path.basename(file_path),
            sheet_names=sheet_names,
            preview_sheet_name=preview_sheet.title,
            preview_rows=preview_rows,
        )

        return _build_text_preview_result(
            file_type="excel",
            preview_method="xlsx_reader",
            content=preview_text,
            has_more=has_more,
            extra_metadata={
                "sheet_names": sheet_names,
                "sheet_count": len(sheet_names),
                "preview_sheet": preview_sheet.title,
                "preview_rows": len(preview_rows),
            },
        )
    except Exception as e:
        return _build_preview_error_result(
            file_type="excel",
            preview_method="xlsx_reader",
            error=f"读取 Excel 文件失败: {str(e)}",
        )


def _extract_pptx(file_path: str, max_pages: int) -> Dict[str, Any]:
    """
    提取 PPT 演示文稿内容

    当前优先使用 PowerPoint COM 导出前若干页截图；
    若运行环境缺少 pywin32，则退回 python-pptx 做文字提取。
    """
    try:
        import pythoncom
        import win32com.client as win32
        return _extract_pptx_via_com(file_path, max_pages, pythoncom, win32)
    except ImportError:
        return _extract_pptx_via_python_pptx(file_path, max_pages)
    except Exception as com_error:
        fallback_result = _extract_pptx_via_python_pptx(file_path, max_pages)
        if fallback_result.get("success"):
            fallback_result.setdefault("metadata", {})["com_fallback_reason"] = str(com_error)
            fallback_result["metadata"]["preview_note"] = "当前未使用 PowerPoint 导出截图，已退回到 python-pptx 文本提取预览。"
            return fallback_result

        return _build_preview_error_result(
            file_type="ppt",
            preview_method="pptx_previewer",
            error=(
                "PPT 预览失败：PowerPoint COM 导出不可用，且 python-pptx 文本提取也失败。"
                f" COM 错误: {str(com_error)}；回退错误: {fallback_result.get('error', '未知错误')}"
            ),
        )


def _extract_pptx_via_com(file_path: str, max_pages: int, pythoncom, win32) -> Dict[str, Any]:
    app = None
    presentation = None
    temp_dir = None

    try:
        pythoncom.CoInitialize()
        temp_dir = Path(tempfile.mkdtemp(prefix="weseeker_ppt_"))
        app = win32.DispatchEx("PowerPoint.Application")
        app.Visible = 1

        try:
            app.WindowState = 2
        except Exception:
            pass

        presentation = app.Presentations.Open(
            os.path.abspath(file_path),
            ReadOnly=1,
            Untitled=0,
            WithWindow=0,
        )

        total_pages = presentation.Slides.Count
        if total_pages == 0:
            return _build_preview_error_result(
                file_type="ppt",
                preview_method="ppt_slide_images",
                error="PPT 没有可预览的幻灯片",
            )

        preview_pages = min(max_pages, total_pages)
        image_paths = []

        for slide_index in range(1, preview_pages + 1):
            slide = presentation.Slides(slide_index)
            image_path = temp_dir / f"slide_{slide_index}.png"
            slide.Export(str(image_path), "PNG")
            if not image_path.exists():
                raise RuntimeError(f"第 {slide_index} 页导出失败")
            image_paths.append(str(image_path))

        return {
            "success": True,
            "file_type": "ppt",
            "preview_method": "ppt_slide_images",
            "content": None,
            "images": image_paths,
            "metadata": {
                "file_name": os.path.basename(file_path),
                "total_pages": total_pages,
                "preview_pages": preview_pages,
                "image_count": len(image_paths),
                "image_paths": image_paths,
                "temp_dir": str(temp_dir),
                "has_more": total_pages > preview_pages,
                "preview_note": "已使用 PowerPoint COM 导出前几页幻灯片截图。",
            },
            "estimated_tokens": 0,
            "error": None,
        }
    finally:
        if presentation is not None:
            try:
                presentation.Close()
            except Exception:
                pass
        if app is not None:
            try:
                app.Quit()
            except Exception:
                pass
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass


def _extract_pptx_via_python_pptx(file_path: str, max_pages: int) -> Dict[str, Any]:
    try:
        from pptx import Presentation
    except ImportError:
        return _build_preview_error_result(
            file_type="ppt",
            preview_method="ppt_text_fallback",
            error="缺少 pywin32 与 python-pptx 依赖，暂时无法预览 PPT",
        )

    try:
        presentation = Presentation(file_path)
        total_pages = len(presentation.slides)
        if total_pages == 0:
            return _build_preview_error_result(
                file_type="ppt",
                preview_method="ppt_text_fallback",
                error="PPT 没有可预览的幻灯片",
            )

        preview_pages = min(max_pages, total_pages)
        slide_blocks = []

        slides = list(presentation.slides)
        for slide_index, slide in enumerate(slides[:preview_pages], start=1):
            text_items = []
            for shape in slide.shapes:
                shape_text = getattr(shape, "text", None)
                if shape_text is None:
                    continue
                text = _clean_inline_whitespace(shape_text)
                if text:
                    text_items.append(text)

            if not text_items:
                continue

            slide_blocks.append(f"第 {slide_index} 页:")
            slide_blocks.extend(text_items[:12])
            slide_blocks.append("")

        if not slide_blocks:
            return _build_preview_error_result(
                file_type="ppt",
                preview_method="ppt_text_fallback",
                error="PPT 中未提取到可预览的文字内容，当前环境又无法导出幻灯片截图",
            )

        content = "\n".join([
            f"演示文稿: {os.path.basename(file_path)}",
            f"总页数: {total_pages}",
            f"当前预览页数: {preview_pages}",
            "",
            *slide_blocks,
        ]).strip()

        return _build_text_preview_result(
            file_type="ppt",
            preview_method="ppt_text_fallback",
            content=content,
            has_more=total_pages > preview_pages,
            extra_metadata={
                "total_pages": total_pages,
                "preview_pages": preview_pages,
                "preview_note": "当前未使用 PowerPoint 导出截图，已退回到 python-pptx 文本提取预览。",
            },
        )
    except Exception as e:
        return _build_preview_error_result(
            file_type="ppt",
            preview_method="ppt_text_fallback",
            error=f"读取 PPT 失败: {str(e)}",
        )


def _extract_pdf(file_path: str, max_pages: int) -> Dict[str, Any]:
    """提取 PDF 前若干页为图片，供多模态 LLM 做摘要。"""
    try:
        render_scale = _get_pdf_render_scale()

        with fitz.open(file_path) as doc:
            total_pages = len(doc)
            if total_pages == 0:
                return {
                    "success": False,
                    "file_type": "pdf",
                    "preview_method": "pdf_page_images",
                    "content": None,
                    "images": None,
                    "metadata": {},
                    "estimated_tokens": 0,
                    "error": "PDF 没有可预览的页面",
                }

            preview_pages = min(max_pages, total_pages)
            temp_dir = Path(tempfile.mkdtemp(prefix="weseeker_pdf_"))
            image_paths = []
            matrix = fitz.Matrix(render_scale, render_scale)

            for page_index in range(preview_pages):
                page = doc.load_page(page_index)
                pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                image_path = temp_dir / f"page_{page_index + 1}.png"
                pixmap.save(str(image_path))
                image_paths.append(str(image_path))

        return {
            "success": True,
            "file_type": "pdf",
            "preview_method": "pdf_page_images",
            "content": None,
            "images": image_paths,
            "metadata": {
                "file_name": os.path.basename(file_path),
                "total_pages": total_pages,
                "preview_pages": preview_pages,
                "image_count": len(image_paths),
                "image_paths": image_paths,
                "render_scale": render_scale,
                "temp_dir": str(temp_dir),
                "has_more": total_pages > preview_pages,
            },
            "estimated_tokens": 0,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "file_type": "pdf",
            "preview_method": "pdf_page_images",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"读取 PDF 失败: {str(e)}",
        }


def _extract_image(file_path: str) -> Dict[str, Any]:
    """提取图片文件信息，供多模态 LLM 做摘要。"""
    try:
        stat = os.stat(file_path)
        return {
            "success": True,
            "file_type": "image",
            "preview_method": "image_file",
            "content": None,
            "images": [file_path],
            "metadata": {
                "file_name": os.path.basename(file_path),
                "file_size": stat.st_size,
                "image_count": 1,
                "image_paths": [file_path],
                "has_more": False,
            },
            "estimated_tokens": 0,
            "error": None,
        }
    except Exception as e:
        return {
            "success": False,
            "file_type": "image",
            "preview_method": "image_file",
            "content": None,
            "images": None,
            "metadata": {},
            "estimated_tokens": 0,
            "error": f"读取图片文件失败: {str(e)}",
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
        "name": "read_file_content",
        "description": "读取文件内容。支持文本文件(.txt/.md/.py/.json等)、Word 文档(.docx，仅正文纯文字预览)、Excel 表格(.xlsx，提取第一个非空工作表前几行)、PPT 演示文稿(.pptx，优先导出前几页截图，缺少 pywin32 时退回文字提取)、图片文件(.png/.jpg/.jpeg/.webp/.bmp/.gif)和 PDF 文件；PDF 当前通过前几页截图进行预览总结，Word 暂不处理图片和复杂版式，Excel 暂不支持 .xls 与复杂图表版式。只能使用 file_index 从搜索结果中选择，避免路径错误。深度 L1/L2/L3 表示预览程度：文本与 Word 默认读取 2000/5000/8000 字，Excel 默认查看 10/50/100 行，PPT/PDF 默认查看前 1/2/3 页。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_index": {
                    "type": "integer",
                    "description": "文件序号（推荐），从搜索结果列表中选择，如 1、2、3 等。优先使用此参数！"
                },
                "file_path": {
                    "type": "string",
                    "description": "文件完整路径（备选），仅在没有搜索结果或读取未搜索的文件时使用"
                },
                "depth": {
                    "type": "string",
                    "description": "预览深度: L1(默认快速预览)/L2(详细)/L3(完整)",
                    "enum": ["L1", "L2", "L3"],
                    "default": "L1"
                }
            },
            "required": []
        }
    }
}


PREVIEW_TOOL_SCHEMA_FOR_DEBUG = {
    "type": "function",
    "function": {
        "name": "read_file_content",
        "description": "[FOR_DEBUG] 读取文件内容。支持文本文件、Word 文档(.docx，仅正文纯文字预览)、Excel 表格(.xlsx，提取第一个非空工作表前几行)、PPT 演示文稿(.pptx，优先导出前几页截图，缺少 pywin32 时退回文字提取)、图片文件和 PDF 文件；仅要求 file_path，适合独立脚本或脱离 Agent 候选文件上下文的调试场景。",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "文件的完整路径"
                },
                "depth": {
                    "type": "string",
                    "description": "读取深度: L1(默认快速预览)/L2(详细)/L3(完整)",
                    "enum": ["L1", "L2", "L3"],
                    "default": "L1"
                }
            },
            "required": ["file_path"]
        }
    }
}
