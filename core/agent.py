"""
Agent 主循环
处理用户输入 → 调用 LLM → 执行 Tool → 返回结果
"""

import json
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List, Dict, Any
from core.llm_router import LLMClient, load_system_prompt
from tools.everything_search import search_files, SEARCH_TOOL_SCHEMA, format_file_size
from tools.file_sender import send_file, SEND_TOOL_SCHEMA
from tools.file_summarizer import file_summarizer, PREVIEW_TOOL_SCHEMA


class Agent:
    """文件管家 Agent"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.system_prompt = load_system_prompt()
        self.conversation_history: List[Dict[str, str]] = []

        # 可用工具列表
        self.tools = [SEARCH_TOOL_SCHEMA, SEND_TOOL_SCHEMA, PREVIEW_TOOL_SCHEMA]

        # 工具函数映射
        self.tool_functions = {
            "search_files": self._execute_search,
            "send_file": self._execute_send,
            "file_summarizer": self._execute_preview
        }

        # 候选文件缓存（用于用户确认发送）
        self.candidate_files: List[Dict] = []

    def process_message(self, user_input: str) -> str:
        """
        处理用户消息

        Args:
            user_input: 用户输入文本

        Returns:
            Agent 回复
        """
        # 添加用户消息到历史
        self.conversation_history.append({
            "role": "user",
            "content": user_input
        })

        # 调用 LLM
        response = self.llm_client.chat(
            messages=self._build_messages(),
            tools=self.tools
        )

        # 处理响应
        return self._handle_response(response)

    def _build_messages(self) -> List[Dict]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        messages.extend(self.conversation_history)
        return messages

    def _handle_response(self, response) -> str:
        """处理 LLM 响应"""
        # 检查是否有工具调用
        tool_calls = self.llm_client.get_tool_calls(response)

        if tool_calls:
            # 执行工具调用
            return self._execute_tool_calls(tool_calls)
        else:
            # 直接返回文本回复
            content = self.llm_client.get_response_content(response)
            if content:
                # 添加到历史
                self.conversation_history.append({
                    "role": "assistant",
                    "content": content
                })
                return content
            return "抱歉，我没有理解你的意思，能再说一遍吗？"

    def _execute_tool_calls(self, tool_calls) -> str:
        """执行工具调用"""
        results = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            arguments = json.loads(tool_call.function.arguments)

            print(f"[调试] 调用工具: {function_name}({arguments})")

            if function_name in self.tool_functions:
                try:
                    result = self.tool_functions[function_name](**arguments)
                    results.append(result)
                except Exception as e:
                    result = f"工具执行出错: {str(e)}"
                    results.append(result)
            else:
                result = f"未知工具: {function_name}"
                results.append(result)

        # 将工具结果反馈给 LLM 获取最终回复
        tool_results_message = {
            "role": "tool",
            "content": "\n".join(results)
        }

        # 添加助手消息（包含工具调用）和工具结果
        self.conversation_history.append({
            "role": "assistant",
            "content": None,
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                } for tc in tool_calls
            ]
        })
        self.conversation_history.append(tool_results_message)

        # 再次调用 LLM 获取最终回复
        response = self.llm_client.chat(
            messages=self._build_messages()
        )

        content = self.llm_client.get_response_content(response)
        if content:
            self.conversation_history.append({
                "role": "assistant",
                "content": content
            })
            return content

        return "处理完成。"

    def _execute_search(self, keyword: str, path: Optional[str] = None, max_results: int = 20) -> str:
        """执行文件搜索"""
        try:
            results = search_files(keyword, path, max_results)

            if not results:
                return f"没有找到包含「{keyword}」的文件。试试换个关键词？"

            # 缓存搜索结果
            self.candidate_files = results

            # 格式化输出 - 包含完整路径供 LLM 使用
            output_lines = [f"找到 {len(results)} 个相关文件："]

            for i, file_info in enumerate(results[:10], 1):  # 最多显示 10 个
                size_str = format_file_size(file_info["size"])
                output_lines.append(
                    f"{i}. {file_info['name']} — {size_str} — 修改于 {file_info['modified']}"
                )
                # 添加完整路径供 LLM 发送时使用
                output_lines.append(f"   完整路径: {file_info['path']}")

            if len(results) > 10:
                output_lines.append(f"\n... 还有 {len(results) - 10} 个结果未显示")

            output_lines.append("\n你要哪个？请告诉我序号，我会用对应的完整路径发送。")

            return "\n".join(output_lines)

        except Exception as e:
            return f"搜索出错: {str(e)}"

    def _execute_send(self, file_index: Optional[int] = None, file_path: Optional[str] = None, target: Optional[str] = None) -> str:
        """
        执行文件发送

        Args:
            file_index: 文件序号（推荐使用，从候选列表中选择）
            file_path: 文件完整路径（备选，直接指定路径）
            target: 发送目标
        """
        # 优先使用序号从缓存获取路径
        if file_index is not None:
            if not self.candidate_files:
                return "❌ 发送失败: 没有可用的搜索结果，请先搜索文件"

            if file_index < 1 or file_index > len(self.candidate_files):
                return f"❌ 发送失败: 序号 {file_index} 无效，请选择 1-{len(self.candidate_files)} 之间的数字"

            file_path = self.candidate_files[file_index - 1]["path"]
            file_name = self.candidate_files[file_index - 1]["name"]
            print(f"[调试] 使用序号 {file_index} 获取路径: {file_path}")

        elif file_path is None:
            return "❌ 发送失败: 请提供 file_index（序号）或 file_path（文件路径）"

        result = send_file(file_path, target)

        if result["success"]:
            return f"✅ 发送成功！文件「{result['file_name']}」已发送到「{result['target']}」"
        else:
            return f"❌ 发送失败: {result['error']}"

    def _execute_preview(self, file_path: str, depth: str = "L1", **kwargs) -> str:
        """
        执行文件预览

        Args:
            file_path: 文件完整路径
            depth: 预览深度 L1/L2/L3
            **kwargs: 其他可选参数
        """
        try:
            # 调用 file_summarizer 提取内容
            result = file_summarizer(file_path, depth=depth)

            if not result.get("success"):
                return f"❌ 预览失败: {result.get('error', '未知错误')}"

            file_type = result.get("file_type", "unknown")
            content = result.get("content", "")
            metadata = result.get("metadata", {})

            # 格式化预览结果
            preview_lines = [f"📄 文件预览: {os.path.basename(file_path)}"]
            preview_lines.append(f"类型: {file_type}")

            if metadata.get("encoding"):
                preview_lines.append(f"编码: {metadata['encoding']}")

            if metadata.get("total_chars"):
                preview_lines.append(f"总字符数: {metadata['total_chars']}")

            if metadata.get("has_more"):
                preview_lines.append("⚠️ 文件内容较长，仅显示部分内容")

            # 如果有文本内容，使用 LLM 进行总结
            if content:
                preview_lines.append("\n📋 内容摘要:\n")

                summary = self._summarize_content(content, file_type, os.path.basename(file_path))
                preview_lines.append(summary)

                # 添加原始内容片段（供 LLM 参考）
                preview_lines.append(f"\n📄 内容片段（前1000字符）:\n```\n{content[:1000]}\n```")

            return "\n".join(preview_lines)

        except Exception as e:
            return f"预览出错: {str(e)}"

    def _summarize_content(self, content: str, file_type: str, file_name: str) -> str:
        """
        使用 LLM 对文件内容进行总结
        """
        try:
            file_type_desc = {
                'text': '文本文件',
                'word': 'Word 文档',
                'excel': 'Excel 表格',
                'ppt': 'PPT 演示文稿',
                'pdf': 'PDF 文档'
            }.get(file_type, '文件')

            prompt = f"""请对以下 {file_type_desc}「{file_name}」的内容进行简要总结。

要求：
1. 用 2-3 句话概括文件的核心内容
2. 如果是结构化文档（如代码、配置），说明其主要功能或用途
3. 如果是普通文本，提取关键信息
4. 总结要简洁明了，不超过 150 字

文件内容：
---
{content[:2000]}
---

请用中文给出总结："""

            response = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是文件管家，擅长快速理解文件内容并给出简洁准确的总结。"},
                    {"role": "user", "content": prompt}
                ]
            )

            summary = self.llm_client.get_response_content(response)
            return summary if summary else "无法生成总结"

        except Exception as e:
            return f"总结生成失败: {str(e)}"

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.candidate_files = []