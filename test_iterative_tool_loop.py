#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
连续工具推理测试脚本（基于项目内真实文件名样例）

测试目标：
1) 正常多轮：search -> read -> 最终回复
2) 重复查询：触发 duplicate_query 早停并由 LLM 生成澄清
3) 澄清失败兜底：触发 [WARNING] reason 前缀
4) 达到上限：触发 max_steps 并由 LLM 生成澄清

说明：
- 使用 FakeLLM 进行可控测试，不依赖真实模型服务
- 使用项目内文件：config/prompts/system_prompt.md、system_prompt_2.md
"""

import json
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.agent import Agent  # noqa: E402


@dataclass
class _FakeFunction:
    name: str
    arguments: str


@dataclass
class _FakeToolCall:
    id: str
    function: _FakeFunction


def make_tool_call(call_id: str, name: str, arguments: Dict[str, Any]) -> _FakeToolCall:
    return _FakeToolCall(
        id=call_id,
        function=_FakeFunction(name=name, arguments=json.dumps(arguments, ensure_ascii=False)),
    )


def response_with_tool_calls(*calls: _FakeToolCall) -> Dict[str, Any]:
    return {"tool_calls": list(calls), "content": None}


def response_with_text(text: str) -> Dict[str, Any]:
    return {"tool_calls": None, "content": text}


class FakeLLM:
    """按预设顺序返回响应的假 LLM。"""

    def __init__(self, scripted: List[Any]):
        self.scripted = list(scripted)
        self.calls: List[Dict[str, Any]] = []

    def chat(self, messages: list, tools: Optional[list] = None, tool_choice: str = "auto") -> Dict[str, Any]:
        self.calls.append(
            {
                "messages_count": len(messages),
                "has_tools": bool(tools),
                "tool_choice": tool_choice,
                "last_role": messages[-1]["role"] if messages else None,
            }
        )

        if not self.scripted:
            raise RuntimeError("FakeLLM scripted responses exhausted")

        item = self.scripted.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def get_tool_calls(self, response: Dict[str, Any]):
        return response.get("tool_calls")

    def get_response_content(self, response: Dict[str, Any]) -> Optional[str]:
        return response.get("content")


def _mock_search_with_project_prompts(agent: Agent):
    """返回绑定了 agent 的 mock search，实现基于项目内 prompt 文件样例。"""

    base_dir = os.path.dirname(os.path.abspath(__file__))
    file_1 = os.path.join(base_dir, "config", "prompts", "system_prompt.md")
    file_2 = os.path.join(base_dir, "config", "prompts", "system_prompt_2.md")

    def _search(keyword: str, path: Optional[str] = None, max_results: int = 20) -> str:
        candidates = [
            {
                "name": "system_prompt.md",
                "path": file_1,
                "modified": "2026-03-01 10:00",
                "size": 1024,
            },
            {
                "name": "system_prompt_2.md",
                "path": file_2,
                "modified": "2026-03-04 22:00",
                "size": 2048,
            },
        ]

        lowered = (keyword or "").lower()
        compact = lowered.replace(" ", "")
        filtered = [item for item in candidates if compact in item["name"].lower().replace(" ", "")]

        if not filtered and ("prompt" in lowered or "系统" in lowered):
            filtered = candidates

        if not filtered:
            agent.candidate_files = []
            return f"没有找到包含「{keyword}」的文件。试试换个关键词？"

        agent.candidate_files = filtered[:max_results]
        lines = [f"找到 {len(agent.candidate_files)} 个相关文件："]
        for idx, item in enumerate(agent.candidate_files, 1):
            lines.append(f"{idx}. {item['name']} — 修改于 {item['modified']}")
            lines.append(f"   完整路径: {item['path']}")
        return "\n".join(lines)

    return _search


def _mock_search_empty(agent: Agent):
    def _search(keyword: str, path: Optional[str] = None, max_results: int = 20) -> str:
        agent.candidate_files = []
        return f"没有找到包含「{keyword}」的文件。试试换个关键词？"

    return _search


def run_case_success(repo_root: str) -> None:
    """场景1：search -> read -> 最终自然回复。"""
    print("\n=== 场景1：正常多轮（search -> read）===")

    fake = FakeLLM(
        scripted=[
            response_with_tool_calls(make_tool_call("c1", "search_files", {"keyword": "system prompt"})),
            response_with_tool_calls(make_tool_call("c2", "read_file_content", {"file_index": 2, "depth": "L1"})),
            response_with_text("这是新版系统提示词，重点增加了迭代工具推理规则与安全约束。"),
            response_with_text("我看了第2个文件，它是新版系统提示词。要我按它继续帮你定位和发送文件吗？"),
        ]
    )

    agent = Agent(debug=True)
    agent.llm_client = fake
    agent.tool_functions["search_files"] = _mock_search_with_project_prompts(agent)

    reply = agent.process_message("帮我找一下 prompt 相关文件，并看看新版那个")
    print("回复:", reply)

    assert "新版" in reply, "场景1失败：未得到预期新版提示"
    assert len(agent.candidate_files) >= 2, "场景1失败：候选文件未正确生成"
    print("[PASS] 场景1")


def run_case_duplicate_query_stop(repo_root: str) -> None:
    """场景2：重复查询触发 duplicate_query 早停。"""
    print("\n=== 场景2：重复查询早停（duplicate_query）===")

    fake = FakeLLM(
        scripted=[
            response_with_tool_calls(make_tool_call("d1", "search_files", {"keyword": "system_prompt", "path": ""})),
            response_with_tool_calls(make_tool_call("d2", "search_files", {"keyword": "system_prompt", "path": ""})),
            response_with_text("这个条件我已经试过了。你希望按文件类型筛选，还是按最近修改时间来缩小范围？"),
        ]
    )

    agent = Agent(debug=True)
    agent.llm_client = fake
    agent.tool_functions["search_files"] = _mock_search_empty(agent)

    reply = agent.process_message("帮我找 system_prompt")
    print("回复:", reply)

    assert "试过" in reply or "筛选" in reply, "场景2失败：未触发预期澄清"
    print("[PASS] 场景2")


def run_case_warning_fallback(repo_root: str) -> None:
    """场景3：澄清生成失败，触发 [WARNING] + 兜底文案。"""
    print("\n=== 场景3：澄清失败兜底（[WARNING]）===")

    fake = FakeLLM(
        scripted=[
            response_with_tool_calls(make_tool_call("w1", "search_files", {"keyword": "system_prompt", "path": ""})),
            response_with_tool_calls(make_tool_call("w2", "search_files", {"keyword": "system_prompt", "path": ""})),
            RuntimeError("mock clarification llm down"),
        ]
    )

    agent = Agent(debug=True)
    agent.llm_client = fake
    agent.tool_functions["search_files"] = _mock_search_empty(agent)

    reply = agent.process_message("帮我找 system_prompt")
    print("回复:\n", reply)

    assert reply.startswith("[WARNING] duplicate_query:"), "场景3失败：未输出 WARNING 前缀"
    assert "你可以补充" in reply, "场景3失败：未输出兜底引导文案"
    print("[PASS] 场景3")


def run_case_max_steps(repo_root: str) -> None:
    """场景4：连续调用触发 max_steps。"""
    print("\n=== 场景4：达到最大轮次（max_steps）===")

    fake = FakeLLM(
        scripted=[
            response_with_tool_calls(make_tool_call("m1", "search_files", {"keyword": "prompt"})),
            response_with_tool_calls(make_tool_call("m2", "send_file", {"file_index": 1})),
            response_with_tool_calls(make_tool_call("m3", "send_file", {"file_index": 1})),
            response_with_tool_calls(make_tool_call("m4", "send_file", {"file_index": 1})),
            response_with_tool_calls(make_tool_call("m5", "send_file", {"file_index": 1})),
            response_with_tool_calls(make_tool_call("m6", "send_file", {"file_index": 1})),
            response_with_text("我已经尝试了多轮自动处理。你可以补充更具体线索（类型/时间/路径）让我继续精准定位。"),
        ]
    )

    agent = Agent(debug=True)
    agent.llm_client = fake
    agent.tool_functions["search_files"] = _mock_search_with_project_prompts(agent)

    reply = agent.process_message("一直帮我试着发 prompt 文件")
    print("回复:", reply)

    assert "多轮" in reply or "具体线索" in reply, "场景4失败：未触发 max_steps 解释"
    print("[PASS] 场景4")


def main() -> int:
    repo_root = os.path.dirname(os.path.abspath(__file__))
    print("=" * 78)
    print("连续工具推理测试（基于项目内 prompt 文件样例）")
    print("=" * 78)
    print(f"项目路径: {repo_root}")

    required = [
        os.path.join(repo_root, "config", "prompts", "system_prompt.md"),
        os.path.join(repo_root, "config", "prompts", "system_prompt_2.md"),
    ]
    for path in required:
        if not os.path.exists(path):
            print(f"[FAIL] 缺少测试样例文件: {path}")
            return 1

    run_case_success(repo_root)
    run_case_duplicate_query_stop(repo_root)
    run_case_warning_fallback(repo_root)
    run_case_max_steps(repo_root)

    print("\n[PASS] 全部场景通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
