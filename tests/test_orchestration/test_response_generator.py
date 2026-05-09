"""Tests for orchestration.response_generator module."""

import pytest

from orchestration.response_generator import ResponseGenerator, GenerationContext
from personas.persona_loader import load_persona


class TestResponseGeneratorInternals:
    """Unit tests for ResponseGenerator helper methods."""

    def test_summarize_tools(self):
        gen = ResponseGenerator()

        class FakeToolResult:
            data = {"J": [10.0, 20.0], "K": [15.0, 25.0]}
            signals = {"b1": True}

        summary = gen._summarize_tools({"kdj": FakeToolResult()})
        assert "kdj" in summary

    def test_summarize_strategies_with_signals(self):
        gen = ResponseGenerator()

        class FakeSignal:
            action = "buy"
            confidence = 0.8
            reason = "B1 confirmed"

        summary = gen._summarize_strategies({"b1": FakeSignal()})
        assert "buy" in summary
        assert "80%" in summary

    def test_summarize_strategies_empty(self):
        gen = ResponseGenerator()

        class FakeSignal:
            action = "hold"
            confidence = 0.0
            reason = ""

        summary = gen._summarize_strategies({"b1": FakeSignal()})
        assert "暂无明确策略信号" in summary

    def test_convert_to_anthropic_messages(self):
        gen = ResponseGenerator()
        messages = [
            {"role": "system", "content": "You are Z."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
        ]
        system, anthropic_msgs = gen._convert_to_anthropic_messages(messages)
        assert system == "You are Z."
        assert len(anthropic_msgs) == 2
        assert anthropic_msgs[0]["role"] == "user"
        assert anthropic_msgs[1]["role"] == "assistant"

    def test_convert_to_anthropic_no_user_first(self):
        """Anthropic requires first message to be from user."""
        gen = ResponseGenerator()
        messages = [
            {"role": "system", "content": "Sys"},
            {"role": "assistant", "content": "Hi"},
        ]
        system, anthropic_msgs = gen._convert_to_anthropic_messages(messages)
        assert anthropic_msgs[0]["role"] == "user"

    def test_build_messages_structure(self):
        gen = ResponseGenerator()
        persona_config = load_persona("zettaranc")
        context = GenerationContext(
            tool_results={},
            strategy_results={},
        )
        messages = gen._build_messages(
            query="Test query",
            persona_config=persona_config,
            context=context,
        )
        assert messages[0]["role"] == "system"
        assert messages[-1]["role"] == "user"
        assert "Test query" in messages[-1]["content"]

    def test_llm_available_no_key(self):
        import os
        original = os.environ.pop("DASHSCOPE_API_KEY", None)
        original2 = os.environ.pop("LLM_API_KEY", None)
        try:
            gen = ResponseGenerator()
            assert not gen.llm_available
        finally:
            if original:
                os.environ["DASHSCOPE_API_KEY"] = original
            if original2:
                os.environ["LLM_API_KEY"] = original2
