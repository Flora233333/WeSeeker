# File Preview Tool - 文件预览工具

## 功能说明

本工具用于预览文件内容，支持多种文件格式的本地内容提取。提取的内容将交由 LLM 进行智能总结。

## 调用方式

```python
file_summarizer(
    file_path: str,           # 文件的完整路径（必填）
    depth: str = "L1",        # 预览深度: "L1"/"L2"/"L3"
    max_chars: int = 2000,    # 文本类最大字符数（L1默认2000）
    max_pages: int = 3,       # PPT/PDF 最大预览页数（L1默认3）
    max_rows: int = 10,       # Excel 最大预览行数（L1默认10）
)
```

## 预览深度说明

| 深度 | 触发条件 | 文本类 | PPT/PDF | Excel |
|------|----------|--------|---------|-------|
| L1 | 默认 | 前2000字符 | 前3页 | 前10行 |
| L2 | 用户说"详细看看"/"多看点" | 前8000字符 | 前6页 | 前30行 |
| L3 | 用户说"全部内容"/"完整的" | 不限 | 全部 | 全部 |

**注意**: L3 深度需要用户确认，因为可能消耗大量 Token。

## 支持的文件类型

### 已实现
- **文本类**: .txt, .md, .markdown, .py, .js, .java, .c, .cpp, .json, .yaml, .xml, .csv, .log, .ini, .sql 等

### 待实现（预留接口）
- **Word**: .docx, .doc
- **Excel**: .xlsx, .xls
- **PPT**: .pptx, .ppt
- **PDF**: .pdf

## 返回值结构

```python
{
    "success": bool,              # 是否成功
    "file_type": str,             # 文件类型: text/word/excel/ppt/pdf/unknown
    "preview_method": str,        # 使用的预览方法
    "content": str | None,        # 提取的文本内容（文本类）
    "images": list[str] | None,   # 生成的预览图路径（PPT/图片类）
    "metadata": {                 # 附加元信息
        "total_lines": int,       # 总行数（文本）
        "total_chars": int,       # 总字符数
        "total_pages": int,       # 总页数（PPT/PDF）
        "sheet_names": list,      # Sheet名列表（Excel）
        "has_more": bool,         # 是否还有未展示内容
    },
    "estimated_tokens": int,      # 预计消耗的 token 数
    "error": str | None,          # 错误信息
}
```

## 使用场景

1. **用户想确认文件内容**: "帮我看看这个文件里是什么"
2. **用户要求总结**: "总结一下这个文档"
3. **多文件选择时**: 用户说"第二个文件是什么内容？"
4. **不确定是否为目标文件**: "这个报告是关于什么的？"

## 工作流程

1. 根据文件扩展名判断文件类型
2. 按文件类型调用对应提取器
3. 提取内容并计算元信息
4. 将提取的内容交给 LLM 生成摘要
5. 返回结构化结果

## 注意事项

1. **不直接调用 LLM**: 本工具只做本地内容提取，LLM 总结由 Agent 层处理
2. **敏感文件**: 如检测到敏感文件（含密码/密钥等），会在提取前进行脱敏处理
3. **大文件**: 文本文件超过 100KB 时，即使 L3 也会限制读取范围
4. **编码处理**: 文本文件自动检测编码（UTF-8/GBK/GB2312/UTF-16/Latin-1）

## 示例调用

```python
# 预览一个 Python 文件
result = file_summarizer(
    file_path="C:\\Users\\xxx\\Desktop\\test.py",
    depth="L1"
)

# 预览一个 Markdown 文件（详细）
result = file_summarizer(
    file_path="C:\\Users\\xxx\\Documents\\readme.md",
    depth="L2",
    max_chars=5000
)
```
