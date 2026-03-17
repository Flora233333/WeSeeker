import math
import re
from typing import Iterable, List, Optional

from openai import OpenAI

from core.config_loader import load_config


TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]")


def tokenize_for_ranking(text: str) -> List[str]:
    if not text:
        return []
    lowered = text.lower()
    tokens = TOKEN_PATTERN.findall(lowered)
    return [token for token in tokens if token.strip()]


def _normalize_provider(provider: str) -> str:
    if not provider:
        return "local_hash"
    return provider.strip().lower()


def _normalize_base_url(base_url: str) -> str:
    normalized = (base_url or "").strip()
    if not normalized:
        normalized = "http://localhost:1234"
    if not normalized.rstrip("/").endswith("/v1"):
        normalized = normalized.rstrip("/") + "/v1"
    return normalized


class LocalHashEmbedder:
    def __init__(self, dimension: int = 768):
        if dimension <= 0:
            raise ValueError("embedding 维度必须大于 0")
        self.dimension = dimension

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        return [self._embed_single(text or "") for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._embed_single(text or "")

    def _embed_single(self, text: str) -> List[float]:
        vector = [0.0] * self.dimension
        tokens = tokenize_for_ranking(text)
        if not tokens:
            return vector

        for token in tokens:
            index = hash(token) % self.dimension
            vector[index] += 1.0

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector

        return [value / norm for value in vector]


class LMStudioEmbedder:
    def __init__(
        self,
        api_base: str,
        model: str,
        api_key: str = "not-needed",
        timeout: int = 60,
        batch_size: int = 16,
    ):
        if not model:
            raise ValueError("LM Studio embedding 模型名不能为空")
        self.model = model
        self.batch_size = max(1, int(batch_size))
        self.client = OpenAI(
            api_key=api_key or "not-needed",
            base_url=_normalize_base_url(api_base),
            timeout=timeout,
        )

    def embed_texts(self, texts: Iterable[str]) -> List[List[float]]:
        items = [text or "" for text in texts]
        if not items:
            return []

        vectors: List[List[float]] = []
        for start in range(0, len(items), self.batch_size):
            batch = items[start:start + self.batch_size]
            response = self.client.embeddings.create(model=self.model, input=batch)
            ordered = sorted(response.data, key=lambda item: item.index)
            vectors.extend([item.embedding for item in ordered])
        return vectors

    def embed_query(self, text: str) -> List[float]:
        response = self.client.embeddings.create(model=self.model, input=[text or ""])
        ordered = sorted(response.data, key=lambda item: item.index)
        return ordered[0].embedding if ordered else []


def create_embedder(config: Optional[dict] = None):
    if config is None:
        config = load_config()

    rag_embedding = config.get("rag", {}).get("embedding", {})
    provider = _normalize_provider(rag_embedding.get("provider", "local_hash"))

    if provider == "lmstudio":
        model = rag_embedding.get("model", "")
        api_base = rag_embedding.get("api_base") or config.get("llm", {}).get("api_base", "http://localhost:1234")
        timeout = int(rag_embedding.get("timeout", config.get("llm", {}).get("local", {}).get("timeout", 60)))
        batch_size = int(rag_embedding.get("batch_size", 16))
        api_key = rag_embedding.get("api_key") or config.get("llm", {}).get("api_key", "not-needed")
        return LMStudioEmbedder(
            api_base=api_base,
            model=model,
            api_key=api_key,
            timeout=timeout,
            batch_size=batch_size,
        )

    dimension = int(rag_embedding.get("dimension", 768))
    return LocalHashEmbedder(dimension=dimension)
