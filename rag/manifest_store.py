import json
import os
from datetime import datetime
from typing import Dict, Optional

from core.config_loader import load_config


def _repo_root() -> str:
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _manifest_dir(config: Optional[dict] = None) -> str:
    if config is None:
        config = load_config()

    directory = config.get("rag", {}).get("manifest", {}).get("directory", "storage/rag_manifests")
    if os.path.isabs(directory):
        return os.path.normpath(directory)
    return os.path.normpath(os.path.join(_repo_root(), directory))


def get_manifest_path(kb_id: str, config: Optional[dict] = None) -> str:
    return os.path.join(_manifest_dir(config), "{0}.json".format(kb_id))


def load_manifest(kb_id: str, config: Optional[dict] = None) -> Dict:
    manifest_path = get_manifest_path(kb_id, config=config)
    if not os.path.exists(manifest_path):
        return {
            "version": 1,
            "kb_id": kb_id,
            "updated_at": None,
            "files": {},
        }

    with open(manifest_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_manifest(kb_id: str, manifest: Dict, config: Optional[dict] = None) -> None:
    directory = _manifest_dir(config)
    os.makedirs(directory, exist_ok=True)
    manifest["kb_id"] = kb_id
    manifest["updated_at"] = datetime.utcnow().isoformat()

    manifest_path = get_manifest_path(kb_id, config=config)
    with open(manifest_path, "w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
