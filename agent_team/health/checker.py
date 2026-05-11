"""Health checking and circuit breaker for Agents."""

import time
from difflib import SequenceMatcher

from agent_team.core.models import Thought, HealthResult


class AgentHealthChecker:
    """Checks if an Agent's output is healthy."""

    MIN_CONTENT_LENGTH = 20
    REPETITIVE_THRESHOLD = 0.9

    def __init__(self):
        self._history: list[Thought] = []

    def check_thought(self, thought: Thought) -> HealthResult:
        issues = []

        # Check 1: Empty or too short
        if not thought.content or len(thought.content.strip()) < self.MIN_CONTENT_LENGTH:
            issues.append("输出过短，可能是空响应")

        # Check 2: Repetitive with history
        if self._is_repetitive(thought):
            issues.append("输出重复，Agent 可能陷入循环")

        # Check 3: Confidence anomaly
        if thought.confidence < 0.0 or thought.confidence > 1.0:
            issues.append("置信度异常")

        # Check 4: Generic content
        if self._is_generic(thought.content):
            issues.append("输出过于泛化，缺乏实质观点")

        # Check 5: Self-contradictory
        if self._is_self_contradictory(thought):
            issues.append("存在自我矛盾")

        self._history.append(thought)
        # Keep only last 10
        if len(self._history) > 10:
            self._history = self._history[-10:]

        return HealthResult(
            is_healthy=len(issues) == 0,
            issues=issues,
            suggestion="重试" if issues else None,
        )

    def _is_repetitive(self, thought: Thought) -> bool:
        if not self._history:
            return False
        for past in self._history[-3:]:
            if past.agent_name == thought.agent_name:
                similarity = SequenceMatcher(None, past.content, thought.content).ratio()
                if similarity > self.REPETITIVE_THRESHOLD:
                    return True
        return False

    def _is_generic(self, content: str) -> bool:
        generic_phrases = [
            "这个问题需要综合考虑",
            "市场有风险，投资需谨慎",
            "建议关注后续走势",
            "需要更多信息才能判断",
        ]
        if not content:
            return True
        generic_count = sum(1 for p in generic_phrases if p in content)
        return generic_count >= 2

    def _is_self_contradictory(self, thought: Thought) -> bool:
        content = thought.content.lower() if thought.content else ""
        bullish = any(w in content for w in ["看多", "买入", "上涨", "机会", "建仓"])
        bearish = any(w in content for w in ["看空", "卖出", "下跌", "风险", "清仓"])
        return bullish and bearish and thought.confidence > 0.5


class AgentCircuitBreaker:
    """Circuit breaker for individual Agents."""

    FAILURE_THRESHOLD = 3
    RECOVERY_TIMEOUT = 120  # seconds

    def __init__(self, agent_name: str):
        self.agent_name = agent_name
        self.failure_count = 0
        self.last_failure_time: float | None = None
        self.state = "closed"  # closed / open / half_open

    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.state == "half_open":
            self.state = "open"
        elif self.failure_count >= self.FAILURE_THRESHOLD:
            self.state = "open"

    def record_success(self):
        if self.state == "half_open":
            self.state = "closed"
            self.failure_count = 0
        else:
            self.failure_count = max(0, self.failure_count - 1)

    def can_execute(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.last_failure_time and (time.time() - self.last_failure_time > self.RECOVERY_TIMEOUT):
                self.state = "half_open"
                return True
            return False
        return True  # half_open

    def get_fallback_thought(self) -> Thought:
        return Thought(
            agent_name=self.agent_name,
            content=f"【{self.agent_name} 当前服务异常，暂时无法参与分析】",
            confidence=0.0,
            key_points=["服务暂不可用"],
            action="unknown",
            is_fallback=True,
        )
