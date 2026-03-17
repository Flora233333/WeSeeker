from typing import List

from rag.embeddings import tokenize_for_ranking
from rag.schemas import ChunkCandidate


def _lexical_score(query: str, text: str) -> float:
    query_tokens = set(tokenize_for_ranking(query))
    text_tokens = set(tokenize_for_ranking(text))
    if not query_tokens or not text_tokens:
        return 0.0

    overlap = len(query_tokens & text_tokens) / float(len(query_tokens))
    phrase_bonus = 0.15 if query.strip() and query.strip().lower() in (text or "").lower() else 0.0
    score = overlap + phrase_bonus
    if score > 1.0:
        return 1.0
    return score


def rerank_chunks(query: str, chunks: List[ChunkCandidate]) -> List[ChunkCandidate]:
    reranked = []
    for chunk in chunks:
        lexical = _lexical_score(query, chunk.chunk_text)
        chunk.rerank_score = round(0.7 * chunk.retrieval_score + 0.3 * lexical, 6)
        reranked.append(chunk)

    reranked.sort(key=lambda item: item.rerank_score, reverse=True)
    return reranked
