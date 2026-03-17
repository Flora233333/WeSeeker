import os
import importlib
from typing import Dict, List, Optional

from core.config_loader import load_config


class ChromaVectorStore:
    def __init__(self, config: Optional[dict] = None):
        if config is None:
            config = load_config()
        self.config = config
        self.persist_directory = self._resolve_persist_directory()
        self._client = None

    def _resolve_persist_directory(self) -> str:
        directory = self.config.get("rag", {}).get("chroma", {}).get("persist_directory", "storage/chroma")
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        if os.path.isabs(directory):
            return os.path.normpath(directory)
        return os.path.normpath(os.path.join(repo_root, directory))

    def _client_instance(self):
        if self._client is None:
            try:
                chromadb = importlib.import_module("chromadb")
            except Exception as exc:
                raise ImportError("无法导入 chromadb，请确认已正确安装且本地依赖可用") from exc
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def _collection_name(self, kb_id: str) -> str:
        return "kb_{0}_chunks".format(kb_id)

    def get_collection(self, kb_id: str):
        client = self._client_instance()
        return client.get_or_create_collection(
            name=self._collection_name(kb_id),
            metadata={"hnsw:space": "cosine"},
        )

    def reset_collection(self, kb_id: str) -> None:
        client = self._client_instance()
        name = self._collection_name(kb_id)
        try:
            client.delete_collection(name=name)
        except Exception:
            pass
        client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})

    def upsert_chunks(self, kb_id: str, chunks: List[Dict]) -> None:
        if not chunks:
            return
        collection = self.get_collection(kb_id)
        collection.upsert(
            ids=[item["id"] for item in chunks],
            documents=[item["document"] for item in chunks],
            metadatas=[item["metadata"] for item in chunks],
            embeddings=[item["embedding"] for item in chunks],
        )

    def delete_file_chunks(self, kb_id: str, file_id: str, chunk_count: int = 0) -> None:
        collection = self.get_collection(kb_id)
        if chunk_count and chunk_count > 0:
            ids = ["{0}:{1}".format(file_id, index) for index in range(int(chunk_count))]
            collection.delete(ids=ids)
            return
        collection.delete(where={"file_id": file_id})

    def query_chunks(self, kb_id: str, query_embedding: List[float], top_k: int):
        collection = self.get_collection(kb_id)
        return collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

    def count(self, kb_id: str) -> int:
        collection = self.get_collection(kb_id)
        return int(collection.count())
