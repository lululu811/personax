import pytest
from unittest.mock import Mock, patch
from knowledge.query import query_knowledge, format_results


@patch("knowledge.query.KnowledgeStore")
@patch("knowledge.query.get_persona_config")
def test_query_knowledge(mock_config, MockStore):
    mock_config.return_value = {"knowledge_bases": ["zettaranc"]}

    mock_store = Mock()
    mock_store.query.return_value = {
        "documents": [["doc1", "doc2"]],
        "metadatas": [[{"source_file": "a.md", "heading_path": "H1"}, {"source_file": "b.md", "heading_path": "H2"}]],
        "distances": [[0.1, 0.2]],
    }
    MockStore.return_value = mock_store

    results = query_knowledge("test", "zettaranc")
    assert "zettaranc" in results


def test_format_results():
    results = {
        "zettaranc": {
            "documents": [["content1", "content2"]],
            "metadatas": [[{"source_file": "a.md", "heading_path": "H1"}, {"source_file": "b.md", "heading_path": "H2"}]],
            "distances": [[0.1, 0.3]],
        }
    }
    formatted = format_results(results)
    assert "a.md > H1" in formatted
    assert "content1" in formatted
