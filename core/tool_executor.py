import json
import warnings
from typing import Any, Callable, Dict, List, Set, Tuple


class ToolExecutor:
    def __init__(self, debug: bool, has_candidates_fn: Callable[[], bool]):
        self.debug = debug
        self.has_candidates_fn = has_candidates_fn

    def _preview_result_text(self, text: str, max_chars: int = 800) -> str:
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... [truncated]"

    def _print_raw_tool_result(self, tool_name: str, signal: str, ok: bool, result: str) -> None:
        if not self.debug:
            return

        print("\n---------------- Raw Tool Result ----------------")
        print(f"tool: {tool_name}")
        print(f"signal: {signal}")
        print(f"ok: {str(ok).lower()}") # 工具执行成功与失败
        print("result:")
        print(self._preview_result_text(result))
        print("--------------------------------------------------")

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
                signal = "invalid_tool_arguments"
                result = f"工具参数不是合法 JSON：{tool_call.function.arguments}"
                step_signals.append(signal)
                self._print_raw_tool_result(function_name, signal, False, result)
                tool_messages.append(
                    self._build_tool_message(
                        tool_call_id=tool_call.id,
                        tool_name=function_name,
                        ok=False,
                        signal=signal,
                        human_text=result,
                    )
                )
                if self.debug:
                    debug_message = f"[调试] 跳过工具 {function_name}：参数 JSON 非法"
                    warnings.warn(debug_message, RuntimeWarning)
                continue

            if self.debug:
                print(f"[调试] 调用工具: {function_name}({arguments})")

            if function_name == "search_files":
                signature = self._build_search_signature(arguments)
                if signature and signature in search_signatures:
                    result = "已跳过重复搜索（同关键词+同路径）。请补充更多线索。"
                    signal = "duplicate_query"
                    step_signals.append(signal)
                    self._print_raw_tool_result(function_name, signal, False, result)
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
                    search_signatures.add(signature) # 会影响到Agent.py文件的search_signatures的变化，是同一个对象

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

            self._print_raw_tool_result(function_name, signal, ok, result)

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
            warnings.warn("[调试] search_files 缺少 keyword 和 path，无法生成去重签名",
                            RuntimeWarning)
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

        if function_name == "list_folder_contents":
            if result_text.startswith("❌") or "打开文件夹出错" in result_text:
                return "list_error", False
            if "是空的" in result_text:
                return "list_empty", True
            if self.has_candidates_fn():
                return "list_has_candidates", True
            return "list_empty", True

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
