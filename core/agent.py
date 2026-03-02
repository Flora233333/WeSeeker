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
from core.llm_client import LLMClient, load_system_prompt
from tools.search import search_files, SEARCH_TOOL_SCHEMA, format_file_size
from tools.sender import send_file, SEND_TOOL_SCHEMA


class Agent:
    """文件管家 Agent"""

    def __init__(self):
        self.llm_client = LLMClient()
        self.system_prompt = load_system_prompt()
        self.conversation_history: List[Dict[str, str]] = []

        # 可用工具列表
        self.tools = [SEARCH_TOOL_SCHEMA, SEND_TOOL_SCHEMA]

        # 工具函数映射
        self.tool_functions = {
            "search_files": self._execute_search,
            "send_file": self._execute_send
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

    def _execute_send(self, file_path: str, target: Optional[str] = None) -> str:
        """执行文件发送"""
        result = send_file(file_path, target)

        if result["success"]:
            return f"✅ 发送成功！文件「{result['file_name']}」已发送到「{result['target']}」"
        else:
            return f"❌ 发送失败: {result['error']}"

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.candidate_files = []