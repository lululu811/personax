"""Tests for orchestration.conversation module."""

import time
import pytest

from orchestration.conversation import (
    ConversationManager,
    ConversationState,
    DiagnosisEngine,
)


class TestConversationState:
    """Unit tests for ConversationState."""

    def test_creation(self):
        s = ConversationState(conversation_id="test-123")
        assert s.conversation_id == "test-123"
        assert s.diagnosis_round == 0
        assert s.diagnosis_route is None
        assert s.answers == {}

    def test_advance_round(self):
        s = ConversationState(conversation_id="x")
        s.advance_round()
        assert s.diagnosis_round == 1
        s.advance_round()
        assert s.diagnosis_round == 2

    def test_add_answer(self):
        s = ConversationState(conversation_id="x")
        s.add_answer(1, {"cycle": "短线", "status": "已持有"})
        assert s.answers[1]["cycle"] == "短线"

    def test_set_route(self):
        s = ConversationState(conversation_id="x")
        s.set_route("A")
        assert s.diagnosis_route == "A"

    def test_history(self):
        s = ConversationState(conversation_id="x")
        s.add_history("user", "hello")
        s.add_history("assistant", "hi")
        recent = s.get_recent_history(n=2)
        assert len(recent) == 2
        assert recent[0]["role"] == "user"
        assert recent[1]["content"] == "hi"

    def test_is_expired(self):
        s = ConversationState(conversation_id="x")
        assert not s.is_expired(ttl_seconds=3600)
        # Simulate old conversation
        s.last_active = time.time() - 4000
        assert s.is_expired(ttl_seconds=3600)

    def test_serialization(self):
        s = ConversationState(
            conversation_id="x",
            persona="zettaranc",
            diagnosis_round=2,
            diagnosis_route="B",
        )
        s.add_answer(1, {"cycle": "短线"})
        data = s.to_dict()
        restored = ConversationState.from_dict(data)
        assert restored.conversation_id == "x"
        assert restored.diagnosis_round == 2
        assert restored.diagnosis_route == "B"
        assert restored.answers[1]["cycle"] == "短线"


class TestConversationManager:
    """Unit tests for ConversationManager."""

    def test_create_and_get(self):
        cm = ConversationManager(ttl_seconds=300)
        cid = cm.create_conversation("zettaranc")
        assert len(cid) == 12

        state = cm.get_state(cid)
        assert state is not None
        assert state.persona == "zettaranc"

    def test_update_and_list(self):
        cm = ConversationManager()
        cid = cm.create_conversation()
        state = cm.get_state(cid)
        state.advance_round()
        cm.update_state(cid, state)

        state2 = cm.get_state(cid)
        assert state2.diagnosis_round == 1
        assert cm.list_active() == [cid]

    def test_expiration(self):
        cm = ConversationManager(ttl_seconds=0.1)
        cid = cm.create_conversation()
        time.sleep(0.2)
        assert cm.get_state(cid) is None
        assert cm.list_active() == []

    def test_delete(self):
        cm = ConversationManager()
        cid = cm.create_conversation()
        cm.delete_conversation(cid)
        assert cm.get_state(cid) is None


class TestDiagnosisEngine:
    """Unit tests for DiagnosisEngine."""

    def test_route_short_term_held(self):
        assert DiagnosisEngine.determine_route("短线", "已持有") == "A"

    def test_route_short_term_buy(self):
        assert DiagnosisEngine.determine_route("短线", "想进场") == "B"

    def test_route_short_term_sell(self):
        assert DiagnosisEngine.determine_route("短线", "想卖出") == "C"

    def test_route_long_term(self):
        assert DiagnosisEngine.determine_route("长线", "") == "D"

    def test_route_unknown(self):
        assert DiagnosisEngine.determine_route("不确定", "不确定") is None

    def test_position_alert_full(self):
        triggered, msg = DiagnosisEngine.check_position_alert("满仓")
        assert triggered
        assert "10%" in msg

    def test_position_alert_numeric_high(self):
        triggered, msg = DiagnosisEngine.check_position_alert("15%")
        assert triggered

    def test_position_alert_safe(self):
        triggered, _ = DiagnosisEngine.check_position_alert("5%")
        assert not triggered

    def test_round1_questions(self):
        qs = DiagnosisEngine.get_round1_questions()
        assert len(qs) == 3
        assert "短线" in qs[0]

    def test_round2_questions_route_a(self):
        qs = DiagnosisEngine.get_round2_questions("A")
        assert len(qs) == 3
        assert "成本" in qs[0]

    def test_round2_questions_route_b(self):
        qs = DiagnosisEngine.get_round2_questions("B")
        assert len(qs) == 4
        assert "J 值" in qs[0]

    def test_generate_diagnosis_a(self):
        answers = {
            1: {"cycle": "短线", "status": "已持有", "position": "20%"},
            2: {"days": "3", "pnl": "浮盈转浮亏", "signal": "B1"},
        }
        result = DiagnosisEngine.generate_diagnosis("A", answers, {})
        assert "少妇战法" in result or "b1" in result or "信息还不够" in result

    def test_generate_diagnosis_b_green_brick(self):
        answers = {
            1: {"cycle": "短线", "status": "想进场"},
            2: {"brick": "绿砖", "j_value": "5", "heard": "听别人说的"},
        }
        result = DiagnosisEngine.generate_diagnosis("B", answers, {})
        assert "绿砖" in result
