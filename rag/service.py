from typing import Optional

from core.config_loader import load_config
from rag.aggregator import aggregate_chunks_to_files
from rag.embeddings import create_embedder
from rag.indexer import KnowledgeIndexer
from rag.knowledge_base_registry import resolve_knowledge_base
from rag.reranker import rerank_chunks
from rag.retriever import KnowledgeRetriever
from rag.vector_store import ChromaVectorStore


class KnowledgeSearchService:
    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = load_config()
        self.config = config
        self.embedder = create_embedder(config=config)
        self.vector_store = ChromaVectorStore(config=config)
        self.indexer = KnowledgeIndexer(config=config)
        self.retriever = KnowledgeRetriever(self.vector_store, self.embedder)

    def index_knowledge_base(self, knowledge_base: str, force: bool = False):
        return self.indexer.build_or_update(knowledge_base=knowledge_base, force=force)

    def search(self, query: str, knowledge_base: str, max_results: int = 5):
        if not query or not query.strip():
            raise ValueError("query 不能为空")

        kb_spec = resolve_knowledge_base(knowledge_base, config=self.config)
        retrieval_top_k = int(self.config.get("rag", {}).get("retrieval", {}).get("top_k", 30))
        max_chunks_per_file = int(self.config.get("rag", {}).get("retrieval", {}).get("max_chunks_per_file", 3))

        chunk_hits = self.retriever.retrieve(query=query, kb_spec=kb_spec, top_k=retrieval_top_k)
        reranked = rerank_chunks(query, chunk_hits)
        file_hits = aggregate_chunks_to_files(
            chunks=reranked,
            max_results=max_results,
            max_chunks_per_file=max_chunks_per_file,
        )

        return {
            "success": True,
            "knowledge_base": kb_spec.kb_id,
            "display_name": kb_spec.display_name,
            "root_path": kb_spec.root_path,
            "query": query,
            "total_chunk_hits": len(chunk_hits),
            "displayed_count": len(file_hits),
            "files": [
                {
                    "index": index,
                    "file_name": file_hit.file_name,
                    "file_path": file_hit.file_path,
                    "relative_path": file_hit.relative_path,
                    "file_score": round(file_hit.file_score, 6),
                    "hit_chunk_count": file_hit.hit_chunk_count,
                    "source_hits": file_hit.source_hits,
                    "evidence_chunks": [
                        {
                            "chunk_index": chunk.chunk_index,
                            "score": round(chunk.rerank_score, 6),
                            "summary": chunk.chunk_summary,
                            "text_preview": chunk.chunk_text[:220].strip(),
                        }
                        for chunk in file_hit.top_chunks
                    ],
                }
                for index, file_hit in enumerate(file_hits, 1)
            ],
            "error": None,
        }
