"""
Agent 主循环
处理用户输入 → 调用 LLM → 执行 Tool → 返回结果
"""

import os
import warnings
from typing import Optional, List, Dict, Set, Any, Tuple
from core.entities import (
    ErrorEvent,
    ERROR_EVENTS,
    PAUSE_EVENTS,
    DEFAULT_PAUSE_EVENT,
    ToolSpec,
)
from core.llm_router import LLMClient, load_system_prompt
from core.reasoning_state import ReasoningState
from core.tool_executor import ToolExecutor
from tools.everything_search import search_files, SEARCH_TOOL_SCHEMA, format_file_size
from tools.folder_lister import list_folder_contents, LIST_FOLDER_TOOL_SCHEMA, format_folder_items
from tools.file_sender import send_file, SEND_TOOL_SCHEMA
from tools.file_summarizer import (
    read_file_content,
    PREVIEW_TOOL_SCHEMA,
    build_summary_prompt,
    build_image_summary_prompt,
    get_summary_system_prompt,
)


def _clean_markdown(text: str) -> str:
    """保守清理常见 Markdown 包装，尽量不破坏正文内容。"""
    if not text:
        return text

    cleaned_lines = []
    in_code_block = False

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        line = raw_line
        if not in_code_block:
            if line.startswith("> "):
                line = line[2:]
            elif line == ">":
                line = ""

            heading = line.lstrip()
            if heading.startswith("#"):
                prefix_len = len(line) - len(heading)
                marker_count = len(heading) - len(heading.lstrip("#"))
                if 1 <= marker_count <= 6 and len(heading) > marker_count and heading[marker_count] == " ":
                    line = line[:prefix_len] + heading[marker_count + 1:]

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()


class Agent:
    """文件管家 Agent"""

    def __init__(self, debug: bool = False):
        self.llm_client = LLMClient()
        self.system_prompt = load_system_prompt()
        self.conversation_history: List[Dict[str, Any]] = []
        self.debug = debug  # 调试模式开关

        self.tool_specs = [
            ToolSpec("search_files", SEARCH_TOOL_SCHEMA, self._execute_search),
            ToolSpec("list_folder_contents", LIST_FOLDER_TOOL_SCHEMA, self._execute_list_folder_contents),
            ToolSpec("send_file", SEND_TOOL_SCHEMA, self._execute_send),
            ToolSpec("read_file_content", PREVIEW_TOOL_SCHEMA, self._execute_read_file),
        ]

        self.tools = [spec.schema for spec in self.tool_specs]
        self.tool_functions = {spec.name: spec.handler for spec in self.tool_specs}
        self.pending_error_event: Optional[ErrorEvent] = None

        # 候选文件缓存（用于用户确认发送）
        self.candidate_files: List[Dict] = []

        # 自动工具推理控制
        self.max_tool_rounds = 5
        self.max_empty_search_streak = 3
        self.max_low_gain_streak = 3

        self.tool_executor = ToolExecutor(
            debug=self.debug,
            # 类似于函数指针，后面可进行.has_candidates_fn()调用，来判断有无candidate_files
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
        history_snapshot = list(self.conversation_history)
        candidate_snapshot = list(self.candidate_files)
        pending_error_snapshot = self.pending_error_event

        try:
            response = self.llm_client.chat(
                messages=self._build_messages(current_user_input=user_input),
                tools=self.tools
            )

            self.conversation_history.append({
                "role": "user",
                "content": user_input
            })

            return self._handle_response(response)
        except Exception:
            self.conversation_history = history_snapshot
            self.candidate_files = candidate_snapshot
            self.pending_error_event = pending_error_snapshot
            raise

    def _build_messages(self, current_user_input: Optional[str] = None) -> List[Dict]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        messages.extend(self.conversation_history)

        if self.pending_error_event is not None:
            messages.append({
                "role": "system",
                "content": self.pending_error_event.system_message
            })
            self.pending_error_event = None

        if current_user_input is not None:
            messages.append({
                "role": "user",
                "content": current_user_input
            })

        return messages

    def _handle_response(self, response) -> str:
        """处理 LLM 响应（支持最多 5 轮连续工具推理）"""
        return self._run_reasoning_loop(response)

    def _print_tool_plan(self, step_count: int, tool_calls: Optional[list]) -> None:
        if not self.debug or not tool_calls:
            return

        print("\n================== LLM Tool Plan ==================")
        print(f"step: {step_count}")
        print(f"tool_calls: {len(tool_calls)}")
        for idx, tool_call in enumerate(tool_calls, 1):
            print(f"{idx}) {tool_call.function.name} {tool_call.function.arguments}")
        print("==================================================")

    def _print_reasoning_state_transition(
        self,
        step_count: int,
        step_signals: List[str],
        before: Dict[str, int],
        after: Dict[str, int],
    ) -> None:
        if not self.debug:
            return

        print("\n================ Reasoning State =================")
        print(f"step: {step_count}")
        print(f"step_signals: {step_signals}")
        print(f"empty_search_streak: {before['empty_search_streak']} -> {after['empty_search_streak']}")
        print(f"duplicate_query_hits: {before['duplicate_query_hits']} -> {after['duplicate_query_hits']}")
        print(f"low_gain_streak: {before['low_gain_streak']} -> {after['low_gain_streak']}")
        print("=================================================")

    def _run_reasoning_loop(self, initial_response) -> str:
        """多轮工具推理循环：有价值就继续，没价值就停止并追问。"""
        response = initial_response
        state = ReasoningState()
        search_signatures: Set[str] = set()

        while True:
            tool_calls = self.llm_client.get_tool_calls(response)
            self._print_tool_plan(state.step_count + 1, tool_calls)

            if not tool_calls:
                content = self.llm_client.get_response_content(response)
                if content:
                    if state.step_count > 0:
                        content = _clean_markdown(content)
                    self.conversation_history.append({
                        "role": "assistant",
                        "content": content
                    })
                    return content # 追问用户，此时state清0

                self.pending_error_event = ERROR_EVENTS["llm_empty_response"]

                debug_message = self.pending_error_event.debug_message or "Unknown LLM empty response"
                warnings.warn(debug_message, RuntimeWarning)

                return self.pending_error_event.user_visible_message

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

            before_state = {
                "empty_search_streak": state.empty_search_streak,
                "duplicate_query_hits": state.duplicate_query_hits,
                "low_gain_streak": state.low_gain_streak,
            }
            state.step_count += 1 # step_count 统计的是“推理轮次”，不是“工具调用个数”
            state.apply_step_signals(step_signals, bool(self.candidate_files))


            after_state = {
                "empty_search_streak": state.empty_search_streak,
                "duplicate_query_hits": state.duplicate_query_hits,
                "low_gain_streak": state.low_gain_streak,
            }
            self._print_reasoning_state_transition(
                step_count=state.step_count,
                step_signals=step_signals,
                before=before_state,
                after=after_state,
            )

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
        pause_event = PAUSE_EVENTS.get(reason, DEFAULT_PAUSE_EVENT)

        candidate_hint = ""
        if self.candidate_files:
            preview_items = self.candidate_files[:3]
            count = len(preview_items)
            lines = []
            for idx, file_info in enumerate(preview_items, 1):
                lines.append(f"{idx}. {file_info.get('name', '未知文件')} — 修改于 {file_info.get('modified', '未知')}")
            candidate_hint = f"\n已有候选文件（{count}个）：\n" + "\n".join(lines)

        prompt = pause_event.system_instruction
        if candidate_hint:
            prompt += candidate_hint
        prompt += "\n\n请根据情况直接输出提示用户的话"

        try:
            response = self.llm_client.chat(
                messages=[{"role": "system", "content": prompt}]
            )
            content = self.llm_client.get_response_content(response)
            if content:
                return _clean_markdown(content)
                # return content
        except Exception as e:
            warning_line = f"[WARNING] {reason}: LLM_clarification_failed ({str(e)})"
            if self.debug:
                warnings.warn(
                    warning_line,
                    RuntimeWarning,
                )
            return pause_event.default_fallback_msg

        warning_line = f"[WARNING] {reason}: LLM_clarification_empty_response"

        if self.debug:
            warnings.warn(
                warning_line,
                RuntimeWarning,
            )
        return pause_event.default_fallback_msg

    def _execute_search(self, keyword: str, path: Optional[str] = None, max_results: int = 20) -> str:
        """执行文件搜索"""
        try:
            results = search_files(keyword, path, max_results)

            if not results:
                self.candidate_files = []
                return f"没有找到包含「{keyword}」的文件。结合上下文试试换个关键词？"

            # 缓存搜索结果
            self.candidate_files = results

            # 格式化输出 - 包含完整路径供 LLM 使用
            output_lines = [f"找到 {len(results)} 个相关文件："]

            for i, file_info in enumerate(results[:max_results], 1):
                if file_info.get("is_dir"):
                    output_lines.append(
                        f"{i}. {file_info['name']} — 文件夹 — 修改于 {file_info['modified']}"
                    )
                else:
                    size_str = format_file_size(file_info["size"])
                    output_lines.append(
                        f"{i}. {file_info['name']} — {size_str} — 文件 — 修改于 {file_info['modified']}"
                    )
                # 添加完整路径供 LLM 发送时使用
                output_lines.append(f"   完整路径: {file_info['path']}")

            if len(results) > max_results:
                output_lines.append(f"\n... 还有 {len(results) - max_results} 个结果未显示")

            output_lines.append(
                "\n你要哪个？请告诉我当前这组结果里的明确序号，而不是路径，我会自己处理来用对应的完整路径发送；"
                "该序号只对应最近一组结果，不对应更早的列表。"
            )

            return "\n".join(output_lines)

        except Exception as e:
            return f"搜索出错: {str(e)}"

    def _resolve_target_folder(
        self,
        folder_index: Optional[int],
    ) -> Tuple[Optional[str], Optional[str]]:
        if folder_index is not None:
            if not self.candidate_files:
                return None, "❌ 打开文件夹失败: 没有可用的候选结果，请先使用search_files搜索文件夹"

            if folder_index < 1 or folder_index > len(self.candidate_files):
                return None, f"❌ 打开文件夹失败: 序号 {folder_index} 无效，请选择 1-{len(self.candidate_files)} 之间的数字"

            target = self.candidate_files[folder_index - 1]
            if not target.get("is_dir"):
                return None, f"❌ 打开文件夹失败: 序号 {folder_index} 对应的不是文件夹，请选择一个文件夹"

            resolved_path = target["path"]
            if self.debug:
                print(f"[调试] 使用序号 {folder_index} 获取文件夹路径: {resolved_path}")
            return resolved_path, None

        return None, "❌ 打开文件夹失败: 必须先调用 search_files 找到目标文件夹，再使用 folder_index 展开"

    def _execute_list_folder_contents(
        self,
        folder_index: Optional[int] = None,
        max_results: int = 50,
    ) -> str:
        """执行文件夹直属内容列举。"""
        resolved_path, error = self._resolve_target_folder(folder_index)
        if error:
            return error
        if resolved_path is None:
            return "❌ 打开文件夹失败: 未解析到文件夹路径"

        try:
            results = list_folder_contents(resolved_path, max_results=max_results)
            folder_name = os.path.basename(os.path.normpath(resolved_path)) or resolved_path

            if not results:
                self.candidate_files = []
                return f"文件夹「{folder_name}」是空的，或我暂时没有读到里面的直属项目。"

            self.candidate_files = results
            return format_folder_items(folder_name, results)
        except Exception as e:
            return f"打开文件夹出错: {str(e)}"

    def _resolve_target_file(
        self,
        file_index: Optional[int],
        file_path: Optional[str],
        action_name: str,
    ) -> Tuple[Optional[str], Optional[str]]:
        if file_index is not None:
            if not self.candidate_files:
                return None, f"❌ {action_name}失败: 没有可用的搜索结果，请先使用search_files搜索文件"

            if file_index < 1 or file_index > len(self.candidate_files):
                return None, f"❌ {action_name}失败: 序号 {file_index} 无效，请选择 1-{len(self.candidate_files)} 之间的数字"

            target = self.candidate_files[file_index - 1]
            if target.get("is_dir"):
                return None, f"❌ {action_name}失败: 序号 {file_index} 对应的是文件夹，请先展开它或选择一个文件"

            resolved_path = target["path"]
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
        images = result.get("images") or []
        metadata = result.get("metadata", {})

        preview_lines = [f"📄 文件预览: {os.path.basename(file_path)}"]
        preview_lines.append(f"类型: {file_type}")

        if metadata.get("encoding"):
            preview_lines.append(f"编码: {metadata['encoding']}")

        if metadata.get("preview_chars"):
            preview_lines.append(f"预览字符数: {metadata['preview_chars']}")

        if metadata.get("preview_sheet"):
            preview_lines.append(f"预览工作表: {metadata['preview_sheet']}")

        if metadata.get("preview_rows"):
            preview_lines.append(f"预览行数: {metadata['preview_rows']}")

        if metadata.get("total_pages"):
            preview_lines.append(f"总页数: {metadata['total_pages']}")

        if metadata.get("preview_pages"):
            preview_lines.append(f"已预览页数: {metadata['preview_pages']}")

        if metadata.get("has_more"):
            preview_lines.append("⚠️ 文件内容较长，仅显示部分内容")

        if content:
            preview_lines.append("\n📋 内容摘要:\n")
            summary = self._summarize_content(content, file_type, os.path.basename(file_path))
            preview_lines.append(summary)
            # preview_lines.append(f"\n📄 内容片段（前1000字符）:\n```\n{content[:1000]}\n```")
        elif images:
            preview_lines.append("\n🖼️ 图片摘要:\n")
            summary = self._summarize_images(images, file_type, os.path.basename(file_path), metadata)
            if metadata.get("used_image_max_edge"):
                preview_lines.append(f"图片长边上限: {metadata['used_image_max_edge']}")
            preview_lines.append(summary)

        return "\n".join(preview_lines)

    def _summarize_content(self, content: str, file_type: str, file_name: str) -> str:
        """
        使用 LLM 对文件内容进行总结
        """
        try:
            prompt = build_summary_prompt(content, file_type, file_name)

            response = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": get_summary_system_prompt()},
                    {"role": "user", "content": prompt}
                ]
            )

            summary = self.llm_client.get_response_content(response)
            return summary if summary else "无法生成总结"

        except Exception as e:
            return f"总结生成失败: {str(e)}"

    def _summarize_images(self, image_paths: List[str], file_type: str, file_name: str, metadata: Dict[str, Any]) -> str:
        """使用多模态 LLM 对图片内容进行总结。"""
        prompt = build_image_summary_prompt(file_type, file_name, metadata)
        retry_edges = self._get_image_retry_edges(file_type)
        last_error = None

        for max_edge in retry_edges:
            try:
                effective_edge = max_edge or self.llm_client._get_multimodal_image_edge(file_type)
                response = self.llm_client.chat(
                    messages=[
                        {"role": "system", "content": get_summary_system_prompt()},
                        self.llm_client.build_multimodal_user_message(
                            prompt,
                            image_paths,
                            file_type=file_type,
                            max_edge_override=max_edge,
                        ),
                    ]
                )

                summary = self.llm_client.get_response_content(response)
                metadata["used_image_max_edge"] = effective_edge
                return summary if summary else "无法生成图片总结"

            except Exception as e:
                last_error = e
                print('----- LLM IMG Process Error -----')
                if not self._is_retryable_image_error(e):
                    break

        return f"图片总结生成失败: {str(last_error)}"

    def _get_image_retry_edges(self, file_type: str) -> List[Optional[int]]:
        if file_type == "pdf":
            return self._build_retry_edge_chain(file_type, [1792, 1536, 1024])
        if file_type == "ppt":
            return self._build_retry_edge_chain(file_type, [2048, 1792, 1536])
        return [None]

    def _build_retry_edge_chain(self, file_type: str, fallbacks: List[int]) -> List[Optional[int]]:
        default_edge = self.llm_client._get_multimodal_image_edge(file_type)
        chain: List[Optional[int]] = [default_edge] 

        for edge in fallbacks:
            if edge < default_edge and edge not in chain:
                chain.append(edge)

        if 1024 < default_edge and 1024 not in chain:
            chain.append(1024)

        return chain # 如果 file_type='pdf', 则返回 [2048, 1792, 1536, 1024]

    def _is_retryable_image_error(self, error: Exception) -> bool:
        error_text = str(error).lower()
        return "failed to process image" in error_text or "image" in error_text and "invalid_request_error" in error_text

    def clear_history(self):
        """清空对话历史"""
        self.conversation_history = []
        self.candidate_files = []
