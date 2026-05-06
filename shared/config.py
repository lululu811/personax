import os
import yaml
from pathlib import Path
from typing import Any

_PROJECT_ROOT = Path(__file__).parent.parent


def load_yaml(name: str) -> dict[str, Any]:
    path = _PROJECT_ROOT / "registry" / f"{name}.yaml"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_registry() -> dict[str, Any]:
    return {
        "personas": load_yaml("personas"),
        "knowledge_bases": load_yaml("knowledge_bases"),
        "data_sources": load_yaml("data_sources"),
        "indicators": load_yaml("indicators"),
    }


def get_persona_config(persona_name: str) -> dict[str, Any]:
    personas = load_yaml("personas")["personas"]
    if persona_name not in personas:
        raise ValueError(f"Unknown persona: {persona_name}")
    return personas[persona_name]


def get_knowledge_base_config(kb_name: str) -> dict[str, Any]:
    kbs = load_yaml("knowledge_bases")["knowledge_bases"]
    if kb_name not in kbs:
        raise ValueError(f"Unknown knowledge base: {kb_name}")
    return kbs[kb_name]


def get_data_source_config(ds_name: str) -> dict[str, Any]:
    sources = load_yaml("data_sources")["data_sources"]
    if ds_name not in sources:
        raise ValueError(f"Unknown data source: {ds_name}")
    return sources[ds_name]


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
