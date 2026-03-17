from typing import List

from rag.schemas import ChunkCandidate, KnowledgeBaseSpec


def distance_to_score(distance) -> float:
    try:
        numeric = float(distance)
    except (TypeError, ValueError):
        return 0.0
    score = 1.0 - numeric
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return score


class KnowledgeRetriever:
    def __init__(self, vector_store, embedder):
        self.vector_store = vector_store
        self.embedder = embedder

    def retrieve(self, query: str, kb_spec: KnowledgeBaseSpec, top_k: int) -> List[ChunkCandidate]:
        response = self.vector_store.query_chunks(
            kb_id=kb_spec.kb_id,
            query_embedding=self.embedder.embed_query(query),
            top_k=top_k,
        )

        documents = (response.get("documents") or [[]])[0]
        metadatas = (response.get("metadatas") or [[]])[0]
        distances = (response.get("distances") or [[]])[0]

        chunks = []
        for document, metadata, distance in zip(documents, metadatas, distances):
            metadata = metadata or {}
            chunks.append(
                ChunkCandidate(
                    source="rag",
                    kb_id=kb_spec.kb_id,
                    file_id=str(metadata.get("file_id", "")),
                    file_path=str(metadata.get("file_path", "")),
                    file_name=str(metadata.get("file_name", "")),
                    relative_path=str(metadata.get("relative_path", "")),
                    chunk_id=str(metadata.get("chunk_id", "")),
                    chunk_index=int(metadata.get("chunk_index", 0)),
                    chunk_text=document or "",
                    chunk_summary=str(metadata.get("chunk_summary", "")),
                    retrieval_score=distance_to_score(distance),
                    metadata=metadata,
                )
            )

        return chunks
