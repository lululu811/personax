from fastapi import APIRouter
import yaml
from pathlib import Path

router = APIRouter(prefix="/personas", tags=["personas"])


@router.get("")
async def list_personas():
    config_path = Path(__file__).parent.parent.parent / "registry" / "personas.yaml"
    with open(config_path) as f:
        config = yaml.safe_load(f)

    personas = []
    for name, cfg in config.get("personas", {}).items():
        personas.append({
            "name": name,
            "display_name": cfg.get("display_name", cfg.get("name", name)),
            "description": cfg.get("description", ""),
            "features": cfg.get("features", {}),
        })
    return personas
