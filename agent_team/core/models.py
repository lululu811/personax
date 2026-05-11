"""Data models for Agent Team framework."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class SessionStatus(Enum):
    IDLE = "idle"
    BRAINSTORMING = "brainstorming"
    REVIEWING = "reviewing"
    DEBATING = "debating"
    CLOSED = "closed"


class ConflictStrategy(Enum):
    CONFIDENCE_WEIGHTED = "confidence_weighted"
    MAJORITY_VOTE = "majority_vote"
    CONSERVATIVE = "conservative"


@dataclass
class Thought:
    """A single thought/opinion from an Agent."""
    agent_name: str
    content: str
    confidence: float = 0.0
    key_points: list[str] = field(default_factory=list)
    action: str = "unknown"  # buy, sell, hold, warning, unknown
    is_rebuttal: bool = False
    is_fallback: bool = False
    metadata: dict = field(default_factory=dict)


@dataclass
class AgentContext:
    """Shared context passed to all Agents in a team."""
    tool_results: Optional[dict] = None
    strategy_results: Optional[dict] = None
    knowledge_snippets: Optional[list[str]] = None
    stock_code: Optional[str] = None
    web_search_results: Optional[str] = None
    debate_history: Optional[list] = None
    is_deep_dive: bool = False


@dataclass
class Synthesis:
    """Moderator's synthesis of multiple thoughts."""
    consensus: str
    disagreements: list[dict]
    recommendation: str
    confidence: float = 0.0


@dataclass
class Round:
    """One round of team analysis."""
    round_num: int
    thoughts: list[Thought]
    moderator_summary: Synthesis


@dataclass
class DebateRound:
    """One round of 1v1 deep-dive debate."""
    round_num: int
    agent_response: Thought
    max_rounds_reached: bool = False


@dataclass
class TeamResult:
    """Final result of a team brainstorming session."""
    rounds: list[Round]
    final_scores: Optional[dict[str, float]] = None
    poster_text: Optional[str] = None
    session_id: Optional[str] = None


@dataclass
class HealthResult:
    """Result of health check on an Agent's output."""
    is_healthy: bool
    issues: list[str] = field(default_factory=list)
    suggestion: Optional[str] = None


@dataclass
class TeamConfig:
    """Configuration for team composition."""
    name: str
    agents: list[str]
    mode: str = "parallel"  # parallel | debate
    moderator_persona: str = "moderator"
    max_agents: int = 4


@dataclass
class AgentWeight:
    """Dynamic weight of an Agent in a team."""
    agent_name: str
    base_weight: float = 1.0
    reputation_score: float = 1.0

    @property
    def effective_weight(self) -> float:
        return self.base_weight * self.reputation_score


@dataclass
class DebateState:
    """Internal state for deep-dive debate."""
    agent_name: str
    round_num: int = 0
    max_rounds: int = 3
    history: list[tuple[str, Thought]] = field(default_factory=list)
