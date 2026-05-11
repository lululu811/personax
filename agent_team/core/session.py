"""TeamSession state machine for interactive brainstorming."""

import uuid
from datetime import datetime

from agent_team.core.models import (
    SessionStatus, Thought, Round, DebateRound, TeamResult,
    DebateState, AgentContext,
)
from agent_team.modes.parallel import ParallelExecutor
from agent_team.modes.debate import DebateExecutor


class SessionLimitError(Exception):
    """Raised when session reaches its limits."""
    pass


class TeamSession:
    """Manages a team brainstorming session with full state machine."""

    MAX_TEAM_ROUNDS = 3
    MAX_DEEP_DIVE_ROUNDS = 3
    MAX_TOTAL_TURNS = 10

    def __init__(self, session_id: str, team):
        self.session_id = session_id
        self.team = team
        self.status = SessionStatus.IDLE
        self.rounds: list[Round] = []
        self.current_deep_dive: str | None = None
        self.current_debate_state: DebateState | None = None
        self.total_turns = 0
        self._context: AgentContext | None = None

    async def start_brainstorm(self, query: str, df=None) -> Round:
        """Start team brainstorming — all agents analyze in parallel."""
        self._check_resource_limits()
        self.status = SessionStatus.BRAINSTORMING

        # Prepare shared context
        self._context = await self._prepare_context(query, df)

        # Select executor based on team mode
        if self.team.mode == "parallel":
            executor = ParallelExecutor(timeout=30.0)
        elif self.team.mode == "debate":
            executor = DebateExecutor()
        else:
            executor = ParallelExecutor(timeout=30.0)

        # Execute
        thoughts = await executor.execute(self.team, query, self._context)

        # Moderator synthesis
        summary = self.team.moderator.synthesize(thoughts, self.team.mode)

        round_result = Round(
            round_num=len(self.rounds) + 1,
            thoughts=thoughts,
            moderator_summary=summary,
        )
        self.rounds.append(round_result)
        self.status = SessionStatus.REVIEWING

        return round_result

    def start_deep_dive(self, agent_name: str, user_challenge: str) -> DebateState:
        """Start 1v1 deep-dive debate with a specific agent."""
        if self.total_turns >= self.MAX_TOTAL_TURNS:
            raise SessionLimitError(f"会话已达到最大交互次数 ({self.MAX_TOTAL_TURNS})，请重新开始")

        if self.current_debate_state and self.current_debate_state.round_num >= self.MAX_DEEP_DIVE_ROUNDS:
            raise SessionLimitError(f"已达到最大辩论轮次 ({self.MAX_DEEP_DIVE_ROUNDS})")

        self.status = SessionStatus.DEBATING
        self.current_deep_dive = agent_name

        if self.current_debate_state is None or self.current_debate_state.agent_name != agent_name:
            self.current_debate_state = DebateState(
                agent_name=agent_name,
                round_num=0,
                max_rounds=self.MAX_DEEP_DIVE_ROUNDS,
            )

        self.total_turns += 1
        return self.current_debate_state

    async def debate_turn(self, user_challenge: str) -> DebateRound:
        """Execute one round of deep-dive debate."""
        if not self.current_debate_state:
            raise ValueError("No active debate")

        agent = self.team.get_agent(self.current_debate_state.agent_name)
        if not agent:
            raise ValueError(f"Agent {self.current_debate_state.agent_name} not found")

        # Build debate context
        debate_context = AgentContext(
            debate_history=self.current_debate_state.history,
            is_deep_dive=True,
        )
        if self._context:
            debate_context.tool_results = self._context.tool_results
            debate_context.strategy_results = self._context.strategy_results

        # Agent responds
        response = await agent.think(user_challenge, debate_context)

        self.current_debate_state.round_num += 1
        self.current_debate_state.history.append((user_challenge, response))

        return DebateRound(
            round_num=self.current_debate_state.round_num,
            agent_response=response,
            max_rounds_reached=self.current_debate_state.round_num >= self.MAX_DEEP_DIVE_ROUNDS,
        )

    def stop_debate(self):
        """User decides to stop deep-dive debate."""
        self.current_deep_dive = None
        self.current_debate_state = None
        self.status = SessionStatus.REVIEWING

    def close(self, scores: dict[str, float]) -> TeamResult:
        """Close session and record feedback."""
        self.status = SessionStatus.CLOSED

        # Record feedback
        try:
            from agent_team.persistence.feedback_store import FeedbackStore
            store = FeedbackStore()
            for agent_name, score in scores.items():
                store.record_feedback(
                    session_id=self.session_id,
                    agent_name=agent_name,
                    user_score=score,
                    query_tags=self._extract_tags(),
                )
        except Exception:
            pass  # Feedback is best-effort

        # Generate text poster
        poster = self._generate_text_poster()

        return TeamResult(
            rounds=self.rounds,
            final_scores=scores,
            poster_text=poster,
            session_id=self.session_id,
        )

    async def _prepare_context(self, query: str, df=None) -> AgentContext:
        """Pre-compute tool data shared by all agents."""
        # TODO: Integrate with existing tool computation
        # For now, return empty context
        return AgentContext()

    def _check_resource_limits(self):
        """Check if session has exceeded limits."""
        if self.total_turns >= self.MAX_TOTAL_TURNS:
            raise SessionLimitError("会话已达到最大交互次数")

    def _extract_tags(self) -> list[str]:
        """Extract query tags for feedback categorization."""
        # TODO: Implement tag extraction from query
        return ["general"]

    def _generate_text_poster(self) -> str:
        """Generate text-based poster from session results."""
        lines = [
            "=" * 50,
            "       PersonaX 团队分析报告",
            "=" * 50,
            "",
        ]

        for round_result in self.rounds:
            lines.append(f"【第 {round_result.round_num} 轮分析】")
            for thought in round_result.thoughts:
                lines.append(f"  {thought.agent_name}: {thought.content[:80]}...")
            lines.append("")

        if self.rounds:
            summary = self.rounds[-1].moderator_summary
            lines.append("【主持人汇总】")
            lines.append(f"  共识: {summary.consensus}")
            lines.append(f"  建议: {summary.recommendation}")
            lines.append("")

        lines.append("=" * 50)
        return "\n".join(lines)
