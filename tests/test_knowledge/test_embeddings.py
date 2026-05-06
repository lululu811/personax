import pytest
from unittest.mock import Mock, patch
from knowledge.embeddings import TongyiEmbedding


@patch.dict("os.environ", {"DASHSCOPE_API_KEY": "fake_key"})
def test_embed_single():
    embedder = TongyiEmbedding()

    with patch("knowledge.embeddings.requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "output": {
                    "embeddings": [
                        {"embedding": [0.1, 0.2, 0.3]}
                    ]
                }
            },
            raise_for_status=lambda: None,
        )

        result = embedder.embed_single("test text")
        assert result == [0.1, 0.2, 0.3]


@patch.dict("os.environ", {"DASHSCOPE_API_KEY": "fake_key"})
def test_embed_batch():
    embedder = TongyiEmbedding()

    with patch("knowledge.embeddings.requests.post") as mock_post:
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "output": {
                    "embeddings": [
                        {"embedding": [0.1, 0.2]},
                        {"embedding": [0.3, 0.4]},
                    ]
                }
            },
            raise_for_status=lambda: None,
        )

        results = embedder.embed(["text1", "text2"])
        assert len(results) == 2
        assert results[0] == [0.1, 0.2]
