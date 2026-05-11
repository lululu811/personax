import pytest
from agent_team.health.checker import AgentHealthChecker, AgentCircuitBreaker
from agent_team.core.models import Thought


class TestAgentHealthChecker:
    def test_empty_content_unhealthy(self):
        checker = AgentHealthChecker()
        thought = Thought(agent_name="test", content="")
        result = checker.check_thought(thought)
        assert result.is_healthy is False
        assert any("输出过短" in i for i in result.issues)

    def test_short_content_unhealthy(self):
        checker = AgentHealthChecker()
        thought = Thought(agent_name="test", content="ok")
        result = checker.check_thought(thought)
        assert result.is_healthy is False

    def test_normal_content_healthy(self):
        checker = AgentHealthChecker()
        thought = Thought(
            agent_name="test",
            content="月线四块砖翻红，中期趋势转多，建议关注量能配合。",
            confidence=0.75,
            key_points=["趋势转多"],
        )
        result = checker.check_thought(thought)
        assert result.is_healthy is True

    def test_self_contradictory(self):
        checker = AgentHealthChecker()
        thought = Thought(
            agent_name="test",
            content="看多，但是建议卖出",
            confidence=0.8,
            action="buy",
        )
        result = checker.check_thought(thought)
        assert any("矛盾" in i for i in result.issues)

    def test_repetitive_detection(self):
        checker = AgentHealthChecker()
        t1 = Thought(agent_name="test", content="看多，建议买入")
        t2 = Thought(agent_name="test", content="看多，建议买入")
        checker._history = [t1]
        result = checker.check_thought(t2)
        assert any("重复" in i for i in result.issues)


class TestAgentCircuitBreaker:
    def test_initial_state_closed(self):
        cb = AgentCircuitBreaker("test_agent")
        assert cb.can_execute() is True
        assert cb.state == "closed"

    def test_opens_after_failures(self):
        cb = AgentCircuitBreaker("test_agent")
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        assert cb.can_execute() is False

    def test_half_open_after_timeout(self):
        import time
        cb = AgentCircuitBreaker("test_agent")
        cb.record_failure()
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "open"
        # Simulate time passing
        cb.last_failure_time = time.time() - 130
        assert cb.can_execute() is True
        assert cb.state == "half_open"

    def test_fallback_thought(self):
        cb = AgentCircuitBreaker("test_agent")
        fallback = cb.get_fallback_thought()
        assert fallback.agent_name == "test_agent"
        assert fallback.is_fallback is True
