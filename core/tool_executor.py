import json
from typing import Any, Callable, Dict, List, Set, Tuple


class ToolExecutor:
    def __init__(self, debug: bool, has_candidates_fn: Callable[[], bool]):
        self.debug = debug
        self.has_candidates_fn = has_candidates_fn

    def execute_tool_calls(
        self,
        tool_calls: list,
        tool_functions: Dict[str, Callable[..., str]],
        search_signatures: Set[str],
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        tool_messages: List[Dict[str, Any]] = []
        step_signals: List[str] = []

        for tool_call in tool_calls:
            function_name = tool_call.function.name

            try:
                arguments = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            except json.JSONDecodeError:
                arguments = {}

            if self.debug:
                print(f"[调试] 调用工具: {function_name}({arguments})")

            if function_name == "search_files":
                signature = self._build_search_signature(arguments)
                if signature and signature in search_signatures:
                    result = "已跳过重复搜索（同关键词+同路径）。请补充更多线索。"
                    signal = "duplicate_query"
                    step_signals.append(signal)
                    tool_messages.append(
                        self._build_tool_message(
                            tool_call_id=tool_call.id,
                            tool_name=function_name,
                            ok=False,
                            signal=signal,
                            human_text=result,
                        )
                    )
                    continue
                if signature:
                    search_signatures.add(signature)

            if function_name in tool_functions:
                try:
                    result = tool_functions[function_name](**arguments)
                    signal, ok = self._infer_tool_signal(function_name, result)
                except Exception as e:
                    result = f"工具执行出错: {str(e)}"
                    signal, ok = "tool_error", False
            else:
                result = f"未知工具: {function_name}"
                signal, ok = "tool_error", False

            step_signals.append(signal)
            tool_messages.append(
                self._build_tool_message(
                    tool_call_id=tool_call.id,
                    tool_name=function_name,
                    ok=ok,
                    signal=signal,
                    human_text=result,
                )
            )

        return tool_messages, step_signals

    def _build_search_signature(self, arguments: Dict[str, Any]) -> str:
        keyword = str(arguments.get("keyword", "")).strip().lower()
        path = str(arguments.get("path", "")).strip().lower()
        if not keyword and not path:
            return ""
        return f"{keyword}|{path}"

    def _infer_tool_signal(self, function_name: str, result_text: str) -> Tuple[str, bool]:
        if function_name == "search_files":
            if "搜索出错" in result_text or "工具执行出错" in result_text:
                return "search_error", False
            if "没有找到" in result_text:
                return "search_empty", True
            if self.has_candidates_fn():
                return "search_has_candidates", True
            return "search_empty", True

        if function_name == "read_file_content":
            if result_text.startswith("❌") or "预览出错" in result_text:
                return "preview_error", False
            return "preview_success", True

        if function_name == "send_file":
            if result_text.startswith("✅"):
                return "send_done", True
            return "send_error", False

        if "工具执行出错" in result_text or "未知工具" in result_text:
            return "tool_error", False
        return "tool_done", True

    def _build_tool_message(self, tool_call_id: str, tool_name: str, ok: bool, signal: str, human_text: str) -> Dict[str, Any]:
        payload = {
            "tool_name": tool_name,
            "ok": ok,
            "signal": signal,
            "human_text": human_text,
        }
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps(payload, ensure_ascii=False),
        }
