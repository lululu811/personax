# tests/test_integration.py
import pytest
from pathlib import Path


class TestPersonaXIntegration:
    def test_registry_loading(self):
        from shared.config import get_persona_config, get_knowledge_base_config, get_data_source_config

        persona = get_persona_config("zettaranc")
        assert persona["name"] == "Z哥"

        kb = get_knowledge_base_config("zettaranc")
        assert kb["collection"] == "zettaranc"

        ds = get_data_source_config("tushare")
        assert ds["enabled"] is True

    def test_data_layer_initialization(self):
        from data.db import Database
        db = Database(":memory:")
        tables = db.conn.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        assert "daily_prices" in table_names
        db.close()

    def test_quant_indicator_discovery(self):
        from quant.registry import discover_indicators, list_indicators
        discover_indicators()
        indicators = list_indicators()
        assert "MA" in indicators
        assert "MACD" in indicators
        assert "RSI" in indicators

    def test_knowledge_chunker(self):
        from knowledge.chunker import MarkdownChunker
        chunker = MarkdownChunker()
        text = "# Title\n\nContent.\n\n## Section\n\nMore content."
        chunks = chunker.split_text(text)
        assert len(chunks) >= 2
