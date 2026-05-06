import pytest
from unittest.mock import Mock, patch
from knowledge.store import KnowledgeStore


@patch("knowledge.store.TongyiEmbedding")
def test_add_and_query(MockEmbedder):
    mock_embedder = Mock()
    mock_embedder.embed.return_value = [[0.1, 0.2, 0.3]]
    mock_embedder.embed_single.return_value = [0.1, 0.2, 0.3]
    MockEmbedder.return_value = mock_embedder

    store = KnowledgeStore(db_path=":memory:")

    chunk = Mock()
    chunk.content = "test content"
    chunk.source_file = "test.md"
    chunk.heading_path = "Title"
    chunk.start_line = 0
    chunk.end_line = 1

    store.add_documents("test_collection", [chunk])

    # Mock query response
    mock_collection = Mock()
    mock_collection.query.return_value = {
        "documents": [["test content"]],
        "metadatas": [[{"source_file": "test.md", "heading_path": "Title"}]],
        "distances": [[0.1]],
    }
    store.client.get_or_create_collection = Mock(return_value=mock_collection)

    results = store.query("test_collection", "test question")
    assert "documents" in results
