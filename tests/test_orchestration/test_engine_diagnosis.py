"""Tests for Engine diagnosis workflow integration."""

import time
import pytest
from dataclasses import dataclass

import pandas as pd
import numpy as np

from orchestration.engine import OrchestrationEngine, OrchestrationRequest
from orchestration.conversation import ConversationManager


def _make_df():
    np.random.seed(42)
    return pd.DataFrame({
        "close": 100 + np.cumsum(np.random.randn(50)),
        "open": 100 + np.cumsum(np.random.randn(50)),
        "high": 102 + np.cumsum(np.random.randn(50)),
        "low": 98 + np.cumsum(np.random.randn(50)),
        "vol": np.random.randint(1000000, 5000000, 50),
    })


class TestEngineDiagnosisFlow:
    """Integration tests for Engine + ConversationManager diagnosis flow."""

    def test_engine_creates_conversation(self):
        engine = OrchestrationEngine()
        df = _make_df()

        # Query with diagnosis keyword "能买吗" triggers diagnosis
        req = OrchestrationRequest(
            query="Z哥，这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp = engine.execute(req)

        assert resp.conversation_id is not None
        assert len(resp.conversation_id) > 0
        assert resp.diagnosis_round == 1
        assert resp.diagnosis_pending is True
        # Round 1 asks cycle/status/position questions
        assert "短线" in resp.persona_analysis or "长线" in resp.persona_analysis

    def test_diagnosis_round1_to_round2(self):
        engine = OrchestrationEngine()
        df = _make_df()

        # Round 1
        req1 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp1 = engine.execute(req1)
        cid = resp1.conversation_id
        assert resp1.diagnosis_round == 1
        assert resp1.diagnosis_pending is True

        # Round 2 - answer round1 questions
        req2 = OrchestrationRequest(
            query="短线，已持有，仓位20%",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        assert resp2.diagnosis_round == 2
        assert resp2.diagnosis_route == "A"
        assert resp2.diagnosis_pending is True

    def test_diagnosis_route_b(self):
        engine = OrchestrationEngine()
        df = _make_df()

        # Round 1
        req1 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp1 = engine.execute(req1)
        cid = resp1.conversation_id

        # Round 2 - route B (short-term, want to buy)
        req2 = OrchestrationRequest(
            query="短线，想进场",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        assert resp2.diagnosis_route == "B"
        assert resp2.diagnosis_round == 2
        assert resp2.diagnosis_pending is True

    def test_diagnosis_route_c(self):
        engine = OrchestrationEngine()
        df = _make_df()

        req1 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp1 = engine.execute(req1)
        cid = resp1.conversation_id

        req2 = OrchestrationRequest(
            query="短线，想卖出",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        assert resp2.diagnosis_route == "C"
        assert resp2.diagnosis_round == 2

    def test_diagnosis_route_d(self):
        engine = OrchestrationEngine()
        df = _make_df()

        req1 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp1 = engine.execute(req1)
        cid = resp1.conversation_id

        req2 = OrchestrationRequest(
            query="长线，持有",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        assert resp2.diagnosis_route == "D"
        assert resp2.diagnosis_round == 2

    def test_diagnosis_full_cycle_route_a(self):
        engine = OrchestrationEngine()
        df = _make_df()

        # Round 1
        req1 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp1 = engine.execute(req1)
        cid = resp1.conversation_id
        assert resp1.diagnosis_pending is True

        # Round 2
        req2 = OrchestrationRequest(
            query="短线，已持有，仓位20%",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        assert resp2.diagnosis_round == 2
        assert resp2.diagnosis_pending is True

        # Round 3 - answer round2 questions
        req3 = OrchestrationRequest(
            query="持仓3天，浮盈转浮亏，信号B1",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp3 = engine.execute(req3)
        assert resp3.diagnosis_round == 3
        assert resp3.diagnosis_pending is False
        assert resp3.persona_analysis is not None
        assert len(resp3.persona_analysis) > 0

    def test_conversation_expiration(self):
        engine = OrchestrationEngine()
        # Override TTL to very short
        engine.conversation_manager = ConversationManager(ttl_seconds=0.1)
        df = _make_df()

        req = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp = engine.execute(req)
        cid = resp.conversation_id
        assert resp.diagnosis_round == 1

        # Wait for expiration
        time.sleep(0.2)

        # Old conversation expired; engine creates a new one with a new ID
        req2 = OrchestrationRequest(
            query="这只票能买吗",
            df=df,
            persona_priority=["zettaranc"],
            conversation_id=cid,
        )
        resp2 = engine.execute(req2)
        # Old conversation expired, new conversation created
        assert resp2.conversation_id != cid
        # New query triggers diagnosis again
        assert resp2.diagnosis_round == 1

    def test_non_diagnosis_query_skips_dialogue(self):
        engine = OrchestrationEngine()
        df = _make_df()

        # Pure technical query without diagnosis keywords
        req = OrchestrationRequest(
            query="计算 MACD 和 RSI",
            df=df,
            persona_priority=["zettaranc"],
        )
        resp = engine.execute(req)

        # Should not start diagnosis, directly give analysis
        assert resp.diagnosis_round == 0
        assert resp.diagnosis_pending is False
        assert resp.tool_results is not None
        assert "macd" in resp.tool_results

    def test_engine_returns_tools_and_analysis(self):
        engine = OrchestrationEngine()
        df = _make_df()

        req = OrchestrationRequest(
            query="茅台 600519 能买吗",
            df=df,
            stock_code="600519.SH",
            persona_priority=["zettaranc"],
        )
        resp = engine.execute(req)

        assert resp.persona_analysis is not None
        assert len(resp.persona_analysis) > 0
        # Should trigger diagnosis because of stock code pattern + "能买吗"
        assert resp.diagnosis_round >= 1
