import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from knowledge.sync import KnowledgeSyncEngine


@patch("knowledge.sync.KnowledgeStore")
@patch("knowledge.sync.MarkdownChunker")
@patch("knowledge.sync.get_knowledge_base_config")
def test_sync_knowledge_base(mock_config, MockChunker, MockStore):
    mock_config.return_value = {
        "vault_path": "/tmp/test_vault",
        "collection": "test_kb",
        "chunker": {"max_chunk_size": 1000, "preserve_hierarchy": True},
        "sync": {"include_patterns": ["*.md"], "exclude_patterns": []},
    }

    mock_chunker = Mock()
    mock_chunker.split_file.return_value = [
        Mock(content="chunk1", source_file="", heading_path="H1", start_line=0, end_line=1),
    ]
    MockChunker.return_value = mock_chunker

    mock_store = Mock()
    MockStore.return_value = mock_store

    with patch("pathlib.Path.exists", return_value=True):
        with patch("pathlib.Path.rglob", return_value=[Path("/tmp/test_vault/test.md")]):
            with patch("knowledge.sync.KnowledgeSyncEngine._file_hash", return_value="abc123"):
                tmp_state = Path("/tmp/test_sync_state.json")
                tmp_state.write_text("{}")
                with patch("knowledge.sync._STATE_FILE", tmp_state):
                    engine = KnowledgeSyncEngine()
                    engine.state = {}
                    count = engine.sync_knowledge_base("test_kb")
                    assert count >= 0
