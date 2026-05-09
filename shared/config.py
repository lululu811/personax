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


def get_wiki_config() -> dict[str, Any]:
    """Get wiki knowledge query configuration."""
    return load_yaml("wiki")["wiki"]


def get_wiki_dirs() -> list[str]:
    """Get enabled wiki directory paths from config (public + personal).

    Priority: env vars > registry/wiki.yaml

    Env vars:
        WIKI_PUBLIC_DIRS   - comma-separated public wiki paths
        WIKI_PERSONAL_DIRS - comma-separated personal wiki paths

    Supports ${ENV_VAR} substitution in paths.
    """
    dirs: list[str] = []

    # 1. Try env vars first
    public_env = os.environ.get("WIKI_PUBLIC_DIRS", "")
    personal_env = os.environ.get("WIKI_PERSONAL_DIRS", "")

    if public_env or personal_env:
        for raw in [public_env, personal_env]:
            for path in raw.split(","):
                path = path.strip()
                path = _resolve_env_vars(path)
                if path and os.path.exists(path):
                    dirs.append(path)
        return dirs

    # 2. Fallback to registry/wiki.yaml
    config = get_wiki_config()
    for category in ("public", "personal"):
        for source in (config.get(category) or {}).values():
            if not source.get("enabled", True):
                continue
            path = _resolve_env_vars(source.get("path", ""))
            if path and os.path.exists(path):
                dirs.append(path)

    return dirs


def _resolve_env_vars(path: str) -> str:
    """Resolve ${ENV_VAR} placeholders in a path string."""
    import re

    pattern = re.compile(r"\$\{([^}]+)\}")

    def replace(match: re.Match) -> str:
        return os.environ.get(match.group(1), "")

    return pattern.sub(replace, path)


def get_env(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key, default)
