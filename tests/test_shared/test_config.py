import pytest
from shared.config import get_persona_config, get_knowledge_base_config


def test_get_persona_config():
    cfg = get_persona_config("zettaranc")
    assert cfg["name"] == "Z哥"
    assert "tushare" in cfg["data_sources"]
    assert cfg["features"]["quant_enabled"] is True


def test_get_knowledge_base_config():
    cfg = get_knowledge_base_config("zettaranc")
    assert cfg["collection"] == "zettaranc"
    assert cfg["chunker"]["strategy"] == "heading"
