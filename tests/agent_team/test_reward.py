import pytest
import tempfile
import os
from agent_team.persistence.feedback_store import FeedbackStore


class TestFeedbackStore:
    @pytest.fixture
    def store(self):
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        store = FeedbackStore(db_path)
        yield store
        os.unlink(db_path)

    def test_record_feedback(self, store):
        store.record_feedback(
            session_id="sess_001",
            agent_name="zettaranc",
            user_score=4.5,
            feedback_text="分析到位",
            query_tags=["技术面", "短线"],
        )
        scores = store.get_agent_scores("zettaranc")
        assert len(scores) == 1
        assert scores[0]["user_score"] == 4.5

    def test_get_agent_reputation(self, store):
        store.record_feedback("sess_001", "zettaranc", 5.0, query_tags=["技术面"])
        store.record_feedback("sess_002", "zettaranc", 4.0, query_tags=["技术面"])
        rep = store.get_agent_reputation("zettaranc", tag="技术面")
        assert rep is not None
        assert rep["sample_count"] == 2
        assert rep["avg_score"] == 4.5

    def test_get_weighted_scores_by_tag(self, store):
        store.record_feedback("sess_001", "zettaranc", 5.0, query_tags=["技术面"])
        store.record_feedback("sess_002", "zettaranc", 3.0, query_tags=["宏观"])
        weights = store.get_weighted_scores("zettaranc")
        assert "技术面" in weights
        assert "宏观" in weights
        assert weights["技术面"] == 5.0
        assert weights["宏观"] == 3.0
