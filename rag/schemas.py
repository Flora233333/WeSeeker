from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class KnowledgeBaseSpec:
    kb_id: str
    display_name: str
    root_path: str
    aliases: List[str] = field(default_factory=list)
    enabled: bool = True
    description: str = ""


@dataclass
class IndexedFileRecord:
    file_id: str
    kb_id: str
    file_path: str
    relative_path: str
    file_name: str
    extension: str
    mtime: float
    size: int
    content_hash: str = ""
    chunk_count: int = 0
    parse_status: str = "indexed"
    last_indexed_at: str = ""


@dataclass
class ChunkCandidate:
    source: str
    kb_id: str
    file_id: str
    file_path: str
    file_name: str
    relative_path: str
    chunk_id: str
    chunk_index: int
    chunk_text: str
    chunk_summary: str
    retrieval_score: float
    rerank_score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FileCandidate:
    kb_id: str
    file_id: str
    file_path: str
    file_name: str
    relative_path: str
    file_score: float
    best_chunk: ChunkCandidate
    top_chunks: List[ChunkCandidate] = field(default_factory=list)
    hit_chunk_count: int = 0
    source_hits: List[str] = field(default_factory=list)


@dataclass
class ExtractionResult:
    success: bool
    file_type: str
    text: str
    error: Optional[str] = None
