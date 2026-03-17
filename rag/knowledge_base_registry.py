import os
from typing import Dict, Optional

from core.config_loader import load_config
from rag.schemas import KnowledgeBaseSpec


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _resolve_path(path_value: str) -> str:
    if not path_value:
        return ""
    if os.path.isabs(path_value):
        return os.path.normpath(path_value)
    return os.path.normpath(os.path.join(_repo_root(), path_value))


def load_knowledge_bases(config: Optional[dict] = None) -> Dict[str, KnowledgeBaseSpec]:
    if config is None:
        config = load_config()

    rag_config = config.get("rag", {})
    kb_config = rag_config.get("knowledge_bases", {})
    knowledge_bases = {}

    for kb_id, raw_spec in kb_config.items():
        if not isinstance(raw_spec, dict):
            continue
        knowledge_bases[kb_id] = KnowledgeBaseSpec(
            kb_id=kb_id,
            display_name=raw_spec.get("display_name", kb_id),
            root_path=_resolve_path(raw_spec.get("root_path", "")),
            aliases=list(raw_spec.get("aliases", [])),
            enabled=bool(raw_spec.get("enabled", True)),
            description=raw_spec.get("description", ""),
        )

    return knowledge_bases


def resolve_knowledge_base(name: str, config: Optional[dict] = None) -> KnowledgeBaseSpec:
    if not name:
        raise ValueError("knowledge_base 不能为空")

    knowledge_bases = load_knowledge_bases(config=config)
    normalized = name.strip().lower()

    for spec in knowledge_bases.values():
        candidates = [spec.kb_id, spec.display_name] + list(spec.aliases)
        if normalized in [candidate.strip().lower() for candidate in candidates if candidate]:
            if not spec.enabled:
                raise ValueError("该知识库已被禁用")
            if not spec.root_path:
                raise ValueError("该知识库未配置根目录")
            return spec

    available = ", ".join(sorted(knowledge_bases.keys())) or "无"
    raise ValueError("未找到知识库: {0}。可用知识库: {1}".format(name, available))
