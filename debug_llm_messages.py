#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
调试脚本 - 展示查询+预览过程中发送给 LLM 的完整内容
"""

import sys
import os
import io
import json

# 设置标准输出编码为 UTF-8
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from WeSeeker.core.llm_router import LLMClient, load_system_prompt
from WeSeeker.tools.everything_search import SEARCH_TOOL_SCHEMA, search_files
from WeSeeker.tools.file_summarizer import file_summarizer, PREVIEW_TOOL_SCHEMA


def print_section(title, content, separator="="):
    """打印带分隔符的章节"""
    print(f"\n{separator * 70}")
    print(f"📝 {title}")
    print(f"{separator * 70}")
    if content:
        print(content)


def debug_llm_messages():
    """调试展示发送给 LLM 的完整消息"""

    print("=" * 70)
    print("🔍 调试: 查询+预览过程中发送给 LLM 的完整内容")
    print("=" * 70)

    # ========== 1. 加载 System Prompt ==========
    system_prompt = load_system_prompt()
    print_section("1. SYSTEM PROMPT (系统提示词)", None)
    print(f"长度: {len(system_prompt)} 字符")
    print(f"前1000字符预览:\n{system_prompt[:1000]}...")

    # ========== 2. 模拟用户查询请求 ==========
    user_query = "帮我找一下 system_prompt.md 文件"
    print_section("2. 用户输入", user_query)

    # ========== 3. 构建第一次请求的消息 ==========
    messages_first_call = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query}
    ]

    tools = [SEARCH_TOOL_SCHEMA, PREVIEW_TOOL_SCHEMA]

    print_section("3. 第一次 LLM 调用 - 发送的消息", None)
    print(f"消息数量: {len(messages_first_call)}")
    print(f"\n消息结构:")
    for i, msg in enumerate(messages_first_call, 1):
        role = msg['role']
        content = msg['content']
        content_preview = content[:200] + "..." if content and len(content) > 200 else content
        print(f"\n  [{i}] Role: {role}")
        print(f"      Content: {content_preview}")

    print(f"\n\n可用工具列表 (Tools):")
    for tool in tools:
        tool_name = tool['function']['name']
        tool_desc = tool['function']['description'][:60] + "..."
        print(f"  - {tool_name}: {tool_desc}")

    # ========== 4. 执行搜索工具 ==========
    print_section("4. 执行搜索工具", None, "-")
    try:
        search_results = search_files("system_prompt.md", max_results=5)
        print(f"找到 {len(search_results)} 个结果")

        # 格式化搜索结果
        search_result_lines = [f"找到 {len(search_results)} 个相关文件："]
        for i, file_info in enumerate(search_results[:3], 1):
            size_str = f"{file_info['size'] / 1024:.1f} KB"
            search_result_lines.append(f"{i}. {file_info['name']} — {size_str}")
            search_result_lines.append(f"   完整路径: {file_info['path']}")

        search_result_text = "\n".join(search_result_lines)
        print(search_result_text)

    except Exception as e:
        search_result_text = f"搜索出错: {e}"
        print(search_result_text)

    # ========== 5. 构建第二次请求的消息（带工具结果）==========
    print_section("5. 第二次 LLM 调用 - 发送的消息（带工具结果）", None)

    messages_second_call = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_query},
        {"role": "assistant", "content": None, "tool_calls": [
            {
                "id": "call_search_001",
                "type": "function",
                "function": {
                    "name": "search_files",
                    "arguments": '{"keyword": "system_prompt.md", "max_results": 5}'
                }
            }
        ]},
        {"role": "tool", "content": search_result_text}
    ]

    print(f"消息数量: {len(messages_second_call)}")
    print(f"\n完整消息结构（JSON 格式）:\n")
    print(json.dumps(messages_second_call, ensure_ascii=False, indent=2))

    # ========== 6. 模拟用户预览请求 ==========
    print_section("6. 用户预览请求", "帮我看看第2个文件的内容，总结一下")

    # 实际执行预览
    if search_results and len(search_results) >= 2:
        target_file = search_results[1]['path']  # 第2个文件
        print(f"\n预览文件: {target_file}")

        preview_result = file_summarizer(target_file, depth="L2")

        if preview_result.get('success'):
            content = preview_result.get('content', '')
            metadata = preview_result.get('metadata', {})

            preview_text = f"""文件预览结果:
文件名: {os.path.basename(target_file)}
文件类型: {preview_result.get('file_type')}
编码: {metadata.get('encoding', 'unknown')}
总字符数: {metadata.get('total_chars', 0)}
预览字符数: {len(content) if content else 0}

文件内容（前2000字符）:
---
{content[:2000] if content else '无内容'}
---"""

            print_section("7. 预览工具返回给 LLM 的内容", preview_text, "-")

            # ========== 7. 构建第三次请求的消息 ==========
            print_section("8. 第三次 LLM 调用 - 完整消息（用于生成最终回复）", None)

            messages_third_call = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": "找到几个相关文件，请看看列表。", "tool_calls": [
                    {
                        "id": "call_search_001",
                        "type": "function",
                        "function": {
                            "name": "search_files",
                            "arguments": '{"keyword": "system_prompt.md"}'
                        }
                    }
                ]},
                {"role": "tool", "content": search_result_text},
                {"role": "user", "content": "帮我看看第2个文件的内容，总结一下"},
                {"role": "assistant", "content": None, "tool_calls": [
                    {
                        "id": "call_preview_001",
                        "type": "function",
                        "function": {
                            "name": "file_summarizer",
                            "arguments": json.dumps({"file_path": target_file, "depth": "L2"}, ensure_ascii=False)
                        }
                    }
                ]},
                {"role": "tool", "content": preview_text}
            ]

            print(f"消息数量: {len(messages_third_call)}")
            print(f"\n完整消息结构（JSON 格式，已截断部分内容）:\n")
            # 截断显示
            display_messages = []
            for msg in messages_third_call:
                display_msg = msg.copy()
                if display_msg.get('content') and len(display_msg['content']) > 500:
                    display_msg['content'] = display_msg['content'][:500] + "...[截断]"
                display_messages.append(display_msg)

            print(json.dumps(display_messages, ensure_ascii=False, indent=2))

            # ========== 8. 实际调用 LLM 生成总结 ==========
            print_section("9. 调用 LLM 生成内容总结", None, "-")

            client = LLMClient()
            summary_prompt = f"""用户想预览文件内容，请根据以下文件内容给出简洁的总结。

文件名: {os.path.basename(target_file)}
文件类型: {preview_result.get('file_type')}

文件内容:
---
{content[:2000] if content else '无内容'}
---

要求:
1. 用 2-3 句话概括文件核心内容
2. 说明文件的主要用途
3. 总结简洁明了，不超过150字

请用中文给出总结:"""

            print("发送给 LLM 的总结请求:")
            print(summary_prompt[:500] + "...")

            response = client.chat(
                messages=[
                    {"role": "system", "content": "你是文件管家，擅长快速理解文件内容并给出简洁准确的总结。"},
                    {"role": "user", "content": summary_prompt}
                ]
            )

            summary = client.get_response_content(response)
            print_section("10. LLM 生成的总结", summary)

    print("\n" + "=" * 70)
    print("✅ 调试完成！")
    print("=" * 70)


if __name__ == "__main__":
    debug_llm_messages()
