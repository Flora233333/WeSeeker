import hashlib
import os
from datetime import datetime
from typing import Dict, List, Optional

from core.config_loader import load_config
from rag.chunker import build_chunk_summary, chunk_text
from rag.embeddings import create_embedder
from rag.extractors import extract_file_text, get_supported_extensions
from rag.knowledge_base_registry import resolve_knowledge_base
from rag.manifest_store import load_manifest, save_manifest
from rag.vector_store import ChromaVectorStore


def _build_file_id(kb_id: str, file_path: str) -> str:
    raw = "{0}:{1}".format(kb_id, os.path.normcase(os.path.abspath(file_path)))
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def _embedding_signature(config: dict) -> str:
    embedding_config = config.get("rag", {}).get("embedding", {})
    provider = str(embedding_config.get("provider", "local_hash")).strip().lower()
    model = str(embedding_config.get("model", "")).strip()
    dimension = str(embedding_config.get("dimension", ""))
    api_base = str(embedding_config.get("api_base") or config.get("llm", {}).get("api_base", "")).strip()
    raw = "|".join([provider, model, dimension, api_base])
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


class KnowledgeIndexer:
    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = load_config()
        self.config = config
        self.embedder = create_embedder(config=config)
        self.vector_store = ChromaVectorStore(config=config)
        self.supported_extensions = set(get_supported_extensions(config))
        chunk_config = config.get("rag", {}).get("chunk", {})
        self.chunk_size = int(chunk_config.get("size", 900))
        self.chunk_overlap = int(chunk_config.get("overlap", 150))

    def build_or_update(self, knowledge_base: str, force: bool = False) -> Dict:
        kb_spec = resolve_knowledge_base(knowledge_base, config=self.config)
        if not os.path.isdir(kb_spec.root_path):
            raise FileNotFoundError("知识库目录不存在: {0}".format(kb_spec.root_path))

        manifest = load_manifest(kb_spec.kb_id, config=self.config)
        current_signature = _embedding_signature(self.config)
        previous_signature = manifest.get("embedding_signature")
        if previous_signature is None and manifest.get("files"):
            force = True
            manifest["files"] = {}
            self.vector_store.reset_collection(kb_spec.kb_id)
        elif previous_signature and previous_signature != current_signature:
            force = True
            manifest["files"] = {}
            self.vector_store.reset_collection(kb_spec.kb_id)

        manifest["embedding_signature"] = current_signature
        file_records = manifest.setdefault("files", {})

        scanned_paths = []
        created = 0
        updated = 0
        skipped = 0
        removed = 0
        failed = 0

        for file_path in self._iter_supported_files(kb_spec.root_path):
            scanned_paths.append(file_path)
            current_stat = os.stat(file_path)
            normalized_path = os.path.normpath(file_path)
            relative_path = os.path.relpath(normalized_path, kb_spec.root_path)
            previous = file_records.get(normalized_path)

            needs_reindex = force or previous is None or self._has_changed(previous, current_stat)
            if not needs_reindex:
                skipped += 1
                continue

            file_id = _build_file_id(kb_spec.kb_id, normalized_path)
            previous_chunk_count = int(previous.get("chunk_count", 0)) if previous else 0
            if previous_chunk_count > 0:
                self.vector_store.delete_file_chunks(kb_spec.kb_id, file_id, chunk_count=previous_chunk_count)

            extraction = extract_file_text(normalized_path)
            if not extraction.success or not extraction.text.strip():
                file_records[normalized_path] = {
                    "file_id": file_id,
                    "relative_path": relative_path,
                    "file_name": os.path.basename(normalized_path),
                    "extension": os.path.splitext(normalized_path)[1].lower(),
                    "mtime": current_stat.st_mtime,
                    "size": current_stat.st_size,
                    "chunk_count": 0,
                    "parse_status": extraction.error or "empty_text",
                    "last_indexed_at": datetime.utcnow().isoformat(),
                }
                failed += 1
                continue

            chunks = chunk_text(extraction.text, self.chunk_size, self.chunk_overlap)
            if not chunks:
                file_records[normalized_path] = {
                    "file_id": file_id,
                    "relative_path": relative_path,
                    "file_name": os.path.basename(normalized_path),
                    "extension": os.path.splitext(normalized_path)[1].lower(),
                    "mtime": current_stat.st_mtime,
                    "size": current_stat.st_size,
                    "chunk_count": 0,
                    "parse_status": "empty_chunks",
                    "last_indexed_at": datetime.utcnow().isoformat(),
                }
                failed += 1
                continue

            embeddings = self.embedder.embed_texts(chunks)
            documents = []
            for index, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                chunk_id = "{0}:{1}".format(file_id, index)
                documents.append(
                    {
                        "id": chunk_id,
                        "document": chunk,
                        "embedding": embedding,
                        "metadata": {
                            "kb_id": kb_spec.kb_id,
                            "file_id": file_id,
                            "file_path": normalized_path,
                            "relative_path": relative_path,
                            "file_name": os.path.basename(normalized_path),
                            "extension": os.path.splitext(normalized_path)[1].lower(),
                            "chunk_id": chunk_id,
                            "chunk_index": index,
                            "mtime": float(current_stat.st_mtime),
                            "size": int(current_stat.st_size),
                            "chunk_summary": build_chunk_summary(chunk),
                        },
                    }
                )

            self.vector_store.upsert_chunks(kb_spec.kb_id, documents)
            file_records[normalized_path] = {
                "file_id": file_id,
                "relative_path": relative_path,
                "file_name": os.path.basename(normalized_path),
                "extension": os.path.splitext(normalized_path)[1].lower(),
                "mtime": current_stat.st_mtime,
                "size": current_stat.st_size,
                "chunk_count": len(chunks),
                "parse_status": "indexed",
                "last_indexed_at": datetime.utcnow().isoformat(),
            }

            if previous is None:
                created += 1
            else:
                updated += 1

        scanned_set = set(scanned_paths)
        for existing_path in list(file_records.keys()):
            if existing_path in scanned_set:
                continue
            file_id = file_records[existing_path].get("file_id")
            if file_id and int(file_records[existing_path].get("chunk_count", 0)) > 0:
                self.vector_store.delete_file_chunks(
                    kb_spec.kb_id,
                    file_id,
                    chunk_count=int(file_records[existing_path].get("chunk_count", 0)),
                )
            del file_records[existing_path]
            removed += 1

        save_manifest(kb_spec.kb_id, manifest, config=self.config)
        return {
            "success": True,
            "knowledge_base": kb_spec.kb_id,
            "root_path": kb_spec.root_path,
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "removed": removed,
            "failed": failed,
            "total_indexed_chunks": self.vector_store.count(kb_spec.kb_id),
        }

    def _iter_supported_files(self, root_path: str) -> List[str]:
        collected = []
        for current_root, _, files in os.walk(root_path):
            for file_name in files:
                extension = os.path.splitext(file_name)[1].lower()
                if extension not in self.supported_extensions:
                    continue
                collected.append(os.path.normpath(os.path.join(current_root, file_name)))
        collected.sort()
        return collected

    @staticmethod
    def _has_changed(previous: Dict, current_stat) -> bool:
        return (
            float(previous.get("mtime", 0)) != float(current_stat.st_mtime)
            or int(previous.get("size", 0)) != int(current_stat.st_size)
        )
