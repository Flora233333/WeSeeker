import argparse
import sys

from rag.knowledge_base_registry import load_knowledge_bases
from tools.search_knowledge import format_knowledge_results


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="WeSeeker RAG 独立测试入口")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("list-kb", help="列出已注册知识库")

    index_parser = subparsers.add_parser("index", help="构建或更新知识库索引")
    index_parser.add_argument("--kb", required=True, help="知识库别名，例如 study")
    index_parser.add_argument("--force", action="store_true", help="强制全量重建")

    search_parser = subparsers.add_parser("search", help="查询知识库")
    search_parser.add_argument("--kb", required=True, help="知识库别名，例如 study")
    search_parser.add_argument("--query", required=True, help="检索问题")
    search_parser.add_argument("--max-results", type=int, default=5, help="最多返回文件数")

    repl_parser = subparsers.add_parser("repl", help="进入交互式知识库查询")
    repl_parser.add_argument("--kb", required=True, help="知识库别名，例如 study")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "list-kb":
        knowledge_bases = load_knowledge_bases()
        if not knowledge_bases:
            print("当前没有已注册知识库。")
            return 0
        for kb_id, spec in sorted(knowledge_bases.items()):
            print("- {0}: {1} -> {2}".format(kb_id, spec.display_name, spec.root_path))
        return 0

    if args.command == "index":
        from rag.service import KnowledgeSearchService

        service = KnowledgeSearchService()
        result = service.index_knowledge_base(args.kb, force=args.force)
        print("索引完成:")
        for key in ["knowledge_base", "root_path", "created", "updated", "skipped", "removed", "failed", "total_indexed_chunks"]:
            print("- {0}: {1}".format(key, result.get(key)))
        return 0

    if args.command == "search":
        from rag.service import KnowledgeSearchService

        service = KnowledgeSearchService()
        result = service.search(query=args.query, knowledge_base=args.kb, max_results=args.max_results)
        print(format_knowledge_results(result))
        return 0

    if args.command == "repl":
        from rag.service import KnowledgeSearchService

        service = KnowledgeSearchService()
        print("进入知识库查询模式，输入 exit 退出。")
        while True:
            query = input("RAG> ").strip()
            if not query:
                continue
            if query.lower() in ("exit", "quit"):
                break
            result = service.search(query=query, knowledge_base=args.kb, max_results=5)
            print(format_knowledge_results(result))
            print()
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
