"""
Agent 主循环
处理用户输入 → 调用 LLM → 执行 Tool → 返回结果
"""

import sys
import os
import re

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional, List, Dict, Set, Any, Tuple
from core.llm_router import LLMClient, load_system_prompt
from core.reasoning_state import ReasoningState
from core.tool_executor import ToolExecutor
from tools.everything_search import search_files, SEARCH_TOOL_SCHEMA, format_file_size
from tools.file_sender import send_file, SEND_TOOL_SCHEMA
from tools.file_summarizer import read_file_content


# 文件预览工具 Schema（支持 file_index 优先从缓存获取路径，避免 LLM 路径幻觉）
PREVIEW_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "read_file_content",
        "description": "读取文件内容。支持文本文件(.txt/.md/.py/.json等)，Word/Excel/PPT/PDF暂不支持。优先使用 file_index 从搜索结果中选择，避免路径错误。深度L1=快速预览(约2000字)，L2=详细(约8000字)，L3=完整(需确认)。",
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


def _clean_markdown(text: str) -> str:
    """简单去除 Markdown 标记，纯文本输出"""
    if not text:
        return text
    # 去除加粗、斜体
    text = re.sub(r'\*\*|\*|__|_', '', text)
    # 去除标题标记
    text = re.sub(r'#{1,6}\s*', '', text)
    # 去除代码块标记，保留内容
    text = re.sub(r'```(\w+)?\n?', '', text)
    text = re.sub(r'```', '', text)
    # 去除行内代码
    text = re.sub(r'`([^`]+)`', r'\1', text)
    # 去除引用标记
    text = re.sub(r'^>\s?', '', text, flags=re.MULTILINE)
    return text


class Agent:
    """文件管家 Agent"""

    def __init__(self, debug: bool = False):
        self.llm_client = LLMClient()
        self.system_prompt = load_system_prompt()
        self.conversation_history: List[Dict[str, Any]] = []
        self.debug = debug  # 调试模式开关

        # 可用工具列表
        self.tools = [SEARCH_TOOL_SCHEMA, SEND_TOOL_SCHEMA, PREVIEW_TOOL_SCHEMA]

        # 工具函数映射
        self.tool_functions = {
            "search_files": self._execute_search,
            "send_file": self._execute_send,
            "read_file_content": self._execute_read_file
        }

        # 候选文件缓存（用于用户确认发送）
        self.candidate_files: List[Dict] = []

        # 自动工具推理控制
        self.max_tool_rounds = 5
        self.max_empty_search_streak = 2
        self.max_low_gain_streak = 2

        self.tool_executor = ToolExecutor(
            debug=self.debug,
            has_candidates_fn=lambda: bool(self.candidate_files),
        )

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
        """处理 LLM 响应（支持最多 5 轮连续工具推理）"""
        return self._run_reasoning_loop(response)

    def _run_reasoning_loop(self, initial_response) -> str:
        """多轮工具推理循环：有价值就继续，没价值就停止并追问。"""
        response = initial_response
        state = ReasoningState()
        search_signatures: Set[str] = set()

        while True:
            tool_calls = self.llm_client.get_tool_calls(response)

            if not tool_calls:
                content = self.llm_client.get_response_content(response)
                if content:
                    if state.step_count > 0:
                        content = _clean_markdown(content)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": content
                    })
                    return content
                return "抱歉，我没有理解你的意思，能再说一遍吗？"

            if state.step_count >= self.max_tool_rounds:
                stop_reply = self._generate_clarification_question("max_steps")
                self.conversation_history.append({
                    "role": "assistant",
                    "content": stop_reply
                })
                return stop_reply

            # 添加 assistant 的 tool_calls 消息
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

            tool_messages, step_signals = self.tool_executor.execute_tool_calls(
                tool_calls=tool_calls,
                tool_functions=self.tool_functions,
                search_signatures=search_signatures,
            )
            self.conversation_history.extend(tool_messages)

            state.step_count += 1
            state.apply_step_signals(step_signals, bool(self.candidate_files))

            stop_reason = state.should_stop(
                max_empty_search_streak=self.max_empty_search_streak,
                max_low_gain_streak=self.max_low_gain_streak,
                has_candidates=bool(self.candidate_files),
            )
            if stop_reason:
                stop_reply = self._generate_clarification_question(stop_reason)
                self.conversation_history.append({
                    "role": "assistant",
                    "content": stop_reply
                })
                return stop_reply

            response = self.llm_client.chat(
                messages=self._build_messages(),
                tools=self.tools
            )

    def _generate_clarification_question(self, reason: str) -> str:
        """让 LLM 基于停止原因生成更灵活的澄清问题。"""
        reason_map = {
            "empty_search": "连续两次搜索无结果",
            "duplicate_query": "搜索条件重复，继续调用收益很低",
            "low_gain": "连续多轮信息增益低",
            "max_steps": "已达到本轮自动推理上限（5轮）",
        }

        reason_text = reason_map.get(reason, "当前线索不足")

        candidate_hint = ""
        if self.candidate_files:
            preview_items = self.candidate_files[:3]
            lines = []
            for idx, file_info in enumerate(preview_items, 1):
                lines.append(f"{idx}. {file_info.get('name', '未知文件')} — 修改于 {file_info.get('modified', '未知')}")
            candidate_hint = "\n已有候选文件（前3个）：\n" + "\n".join(lines)

        prompt = f"""你是文件管家。当前自动工具推理需要暂停，请根据原因给用户一个简短、自然、可执行的澄清问题。

约束：
1. 只问 1 个最关键问题，避免连环提问
2. 语气自然，不要机械模板
3. 问题要能直接帮助下一步搜索（优先：文件类型 / 时间范围 / 路径范围）
4. 如果已有候选文件，优先引导用户选序号或补充区分条件
5. 回复控制在 1-2 句话

暂停原因：{reason_text}{candidate_hint}

请直接输出给用户的话："""

        try:
            response = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是文件管家，擅长在信息不足时提出最小必要澄清问题。"},
                    {"role": "user", "content": prompt}
                ]
            )
            content = self.llm_client.get_response_content(response)
            if content:
                return _clean_markdown(content)
        except Exception as e:
            warning_line = f"[WARNING] {reason}: LLM_clarification_failed ({str(e)})"
            if self.debug:
                print(warning_line)
            return (
                warning_line + "\n"
                + self._build_warning_fallback(reason)
            )

        warning_line = f"[WARNING] {reason}: LLM_clarification_empty_response"
        if self.debug:
            print(warning_line)
        return (
            warning_line + "\n"
            + self._build_warning_fallback(reason)
        )

    def _build_warning_fallback(self, reason: str) -> str:
        """仅在 LLM 澄清生成失败时使用的兜底文案。"""
        if self.candidate_files:
            return (
                f"我先停一下，避免无效调用。当前有 {len(self.candidate_files)} 个候选，"
                "你可以直接告诉我序号，或补充文件类型/时间范围。"
            )

        if reason == "empty_search":
            return "我连续两次都没找到结果。你可以补充一个关键信息吗：文件类型、时间范围，或大概路径（桌面/下载/文档）？"
        if reason == "duplicate_query":
            return "同样的搜索条件我已经试过啦。你可以补充一个新的线索吗，比如文件类型或大概修改时间？"
        if reason == "low_gain":
            return "继续搜索的信息增益很低。你更想按文件类型筛选，还是按时间范围筛选？"
        if reason == "max_steps":
            return "我先停在这里避免无效调用。你可以补充一个更具体线索（文件类型/时间/路径），我再继续精准查找。"
        return "为了更快找到目标文件，你可以再补充一个关键信息吗？"

    def _execute_search(self, keyword: str, path: Optional[str] = None, max_results: int = 20) -> str:
        """执行文件搜索"""
        try:
            results = search_files(keyword, path, max_results)

            if not results:
                self.candidate_files = []
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

    def _resolve_target_file(
        self,
        file_index: Optional[int],
        file_path: Optional[str],
        action_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        if file_index is not None:
            if not self.candidate_files:
                return None, f"❌ {action_name}失败: 没有可用的搜索结果，请先搜索文件"

            if file_index < 1 or file_index > len(self.candidate_files):
                return None, f"❌ {action_name}失败: 序号 {file_index} 无效，请选择 1-{len(self.candidate_files)} 之间的数字"

            resolved_path = self.candidate_files[file_index - 1]["path"]
            if self.debug:
                debug_action = "获取读取路径" if action_name == "读取" else "获取路径"
                print(f"[调试] 使用序号 {file_index} {debug_action}: {resolved_path}")
            return resolved_path, None

        if file_path is None:
            return None, f"❌ {action_name}失败: 请提供 file_index（序号）或 file_path（文件路径）"

        return file_path, None

    def _execute_send(self, file_index: Optional[int] = None, file_path: Optional[str] = None, target: Optional[str] = None) -> str:
        """
        执行文件发送

        Args:
            file_index: 文件序号（推荐使用，从候选列表中选择）
            file_path: 文件完整路径（备选，直接指定路径）
            target: 发送目标
        """
        resolved_path, error = self._resolve_target_file(file_index, file_path, action_name="发送")
        if error:
            return error
        if resolved_path is None:
            return "❌ 发送失败: 未解析到文件路径"

        result = send_file(resolved_path, target)

        if result["success"]:
            return f"✅ 发送成功！文件「{result['file_name']}」已发送到「{result['target']}」"
        else:
            return f"❌ 发送失败: {result['error']}"

    def _execute_read_file(self, file_index: Optional[int] = None, file_path: Optional[str] = None, depth: str = "L1", **kwargs) -> str:
        """
        执行文件内容读取

        Args:
            file_index: 文件序号（推荐使用，从候选列表中选择）
            file_path: 文件完整路径（备选，直接指定路径）
            depth: 读取深度 L1/L2/L3
            **kwargs: 其他可选参数
        """
        resolved_path, error = self._resolve_target_file(file_index, file_path, action_name="读取")
        if error:
            return error
        if resolved_path is None:
            return "❌ 读取失败: 未解析到文件路径"

        try:
            result = self._extract_preview_data(resolved_path, depth)
            if not result.get("success"):
                return f"❌ 预览失败: {result.get('error', '未知错误')}"
            return self._render_preview_response(resolved_path, result)

        except Exception as e:
            return f"预览出错: {str(e)}"

    def _extract_preview_data(self, file_path: str, depth: str) -> Dict[str, Any]:
        return read_file_content(file_path, depth=depth)

    def _render_preview_response(self, file_path: str, result: Dict[str, Any]) -> str:
        file_type = result.get("file_type", "unknown")
        content = result.get("content", "")
        metadata = result.get("metadata", {})

        preview_lines = [f"📄 文件预览: {os.path.basename(file_path)}"]
        preview_lines.append(f"类型: {file_type}")

        if metadata.get("encoding"):
            preview_lines.append(f"编码: {metadata['encoding']}")

        if metadata.get("total_chars"):
            preview_lines.append(f"总字符数: {metadata['total_chars']}")

        if metadata.get("has_more"):
            preview_lines.append("⚠️ 文件内容较长，仅显示部分内容")

        if content:
            preview_lines.append("\n📋 内容摘要:\n")
            summary = self._summarize_content(content, file_type, os.path.basename(file_path))
            preview_lines.append(summary)
            preview_lines.append(f"\n📄 内容片段（前1000字符）:\n```\n{content[:1000]}\n```")

        return "\n".join(preview_lines)

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
