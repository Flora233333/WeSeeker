from typing import Dict, Optional

from rag.service import KnowledgeSearchService


def _shorten_text(text: str, max_chars: int = 180) -> str:
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[:max_chars].rstrip() + "..."


def search_knowledge(query: str, knowledge_base: str, max_results: int = 5) -> Dict:
    service = KnowledgeSearchService()
    return service.search(query=query, knowledge_base=knowledge_base, max_results=max_results)


def format_knowledge_results(result: Dict) -> str:
    if not result.get("success"):
        return "知识库检索失败: {0}".format(result.get("error", "未知错误"))

    files = result.get("files", [])
    if not files:
        return "在知识库「{0}」里没有找到和「{1}」相关的内容。".format(
            result.get("display_name") or result.get("knowledge_base"),
            result.get("query", ""),
        )

    kb_name = result.get("display_name") or result.get("knowledge_base")
    lines = [
        "知识库: {0}".format(kb_name),
        "查询: {0}".format(result.get("query", "")),
        "命中文件: {0} 个 | 命中 chunk: {1} 个".format(len(files), result.get("total_chunk_hits", 0)),
        "",
        "最相关文件:"
    ]

    for item in files:
        relative_path = item.get("relative_path") or item.get("file_name") or ""
        evidence = item.get("evidence_chunks") or []
        best_evidence = evidence[0] if evidence else {}
        preview = best_evidence.get("summary") or best_evidence.get("text_preview") or ""

        lines.append(
            "[{0}] {1}".format(
                item.get("index"),
                relative_path,
            )
        )
        lines.append(
            "  score={0} | 命中 chunks={1}".format(
                item.get("file_score"),
                item.get("hit_chunk_count"),
            )
        )
        if preview:
            lines.append("  证据: {0}".format(_shorten_text(preview)))
        if item.get("file_path"):
            lines.append("  路径: {0}".format(item.get("file_path")))
        lines.append("")

    return "\n".join(lines).rstrip()


SEARCH_KNOWLEDGE_TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "search_knowledge",
        "description": "在预注册知识库中检索文件内容。仅对指定知识库目录内已向量化的文件内容生效。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "用户想查找的主题、概念或内容描述。"
                },
                "knowledge_base": {
                    "type": "string",
                    "description": "知识库别名，例如 study。必须是预注册知识库，不能随意填写路径。"
                },
                "max_results": {
                    "type": "integer",
                    "description": "最多返回多少个文件结果，默认 5。",
                    "default": 5
                }
            },
            "required": ["query", "knowledge_base"]
        }
    }
}
