from collections import defaultdict
from typing import Dict, List

from rag.schemas import ChunkCandidate, FileCandidate


def aggregate_chunks_to_files(
    chunks: List[ChunkCandidate],
    max_results: int,
    max_chunks_per_file: int,
) -> List[FileCandidate]:
    grouped = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.file_path].append(chunk)

    files: List[FileCandidate] = []
    for file_path, file_chunks in grouped.items():
        ordered = sorted(file_chunks, key=lambda item: item.rerank_score, reverse=True)
        top_chunks = ordered[:max_chunks_per_file]
        best_chunk = top_chunks[0]
        files.append(
            FileCandidate(
                kb_id=best_chunk.kb_id,
                file_id=best_chunk.file_id,
                file_path=file_path,
                file_name=best_chunk.file_name,
                relative_path=best_chunk.relative_path,
                file_score=best_chunk.rerank_score,
                best_chunk=best_chunk,
                top_chunks=top_chunks,
                hit_chunk_count=len(file_chunks),
                source_hits=sorted(list({chunk.source for chunk in file_chunks})),
            )
        )

    files.sort(key=lambda item: item.file_score, reverse=True)
    return files[:max_results]
