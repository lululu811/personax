"""Reward engine for dynamic weight adjustment."""

from agent_team.core.models import AgentWeight
from agent_team.persistence.feedback_store import FeedbackStore


def _map_score_to_reputation(avg_score: float) -> float:
    """Map 1-5 score to reputation multiplier (0.5 - 1.5)."""
    # 1.0 -> 0.5, 3.0 -> 1.0, 5.0 -> 1.5
    return 0.5 + (avg_score - 1.0) * 0.25


class RewardEngine:
    """Handles user feedback and computes agent weights."""

    def __init__(self, store: FeedbackStore = None):
        self.store = store or FeedbackStore()

    def record_feedback(
        self,
        session_id: str,
        agent_name: str,
        user_score: float,
        feedback_text: str = "",
        query_tags: list[str] = None,
    ):
        """Record user feedback for an agent."""
        self.store.record_feedback(
            session_id=session_id,
            agent_name=agent_name,
            user_score=user_score,
            feedback_text=feedback_text,
            query_tags=query_tags or ["general"],
        )

    def get_agent_weights(
        self,
        agent_names: list[str],
        query_tags: list[str] = None,
    ) -> dict[str, AgentWeight]:
        """Get current weights for agents."""
        weights = {}
        for name in agent_names:
            # Get global reputation
            global_rep = self.store.get_agent_reputation(name, tag="global")
            if global_rep and global_rep["sample_count"] > 0:
                rep_score = _map_score_to_reputation(global_rep["avg_score"])
            else:
                rep_score = 1.0

            # If query tags provided, blend with tag-specific scores (weighted by sample count)
            if query_tags:
                tag_scores = []
                tag_samples = 0
                for tag in query_tags:
                    rep = self.store.get_agent_reputation(name, tag=tag)
                    if rep and rep["sample_count"] > 0:
                        tag_scores.append(_map_score_to_reputation(rep["avg_score"]) * rep["sample_count"])
                        tag_samples += rep["sample_count"]
                if tag_scores and tag_samples > 0:
                    if global_rep and global_rep["sample_count"] > 0:
                        global_weighted = _map_score_to_reputation(global_rep["avg_score"]) * global_rep["sample_count"]
                        total_samples = global_rep["sample_count"] + tag_samples
                        rep_score = (global_weighted + sum(tag_scores)) / total_samples
                    else:
                        rep_score = sum(tag_scores) / tag_samples

            weights[name] = AgentWeight(
                agent_name=name,
                base_weight=1.0,
                reputation_score=rep_score,
            )

        return weights

    def get_personalized_team(
        self,
        query: str,
        available_agents: list[str],
        top_k: int = 3,
    ) -> list[AgentWeight]:
        """Select top-k agents based on query and historical performance."""
        # Extract simple tags from query
        tags = self._extract_query_tags(query)

        weights = self.get_agent_weights(available_agents, query_tags=tags)

        # Sort by effective weight
        sorted_weights = sorted(
            weights.values(),
            key=lambda w: w.effective_weight,
            reverse=True,
        )

        # Exploration: 15% chance to include a lower-ranked agent
        selected = sorted_weights[:top_k]
        if len(sorted_weights) > top_k and self._should_explore():
            # Add one random lower-ranked agent
            import random
            explorer = random.choice(sorted_weights[top_k:])
            selected.append(explorer)

        return selected

    def _extract_query_tags(self, query: str) -> list[str]:
        """Extract tags from query for categorization."""
        tags = []
        tag_keywords = {
            "技术面": ["技术", "指标", "K线", "MACD", "KDJ", "均线"],
            "宏观": ["宏观", "经济", "政策", "利率", "GDP", "CPI"],
            "基本面": ["财报", "基本面", "ROE", "利润", "营收", "估值"],
            "短线": ["短线", "超短", "日内", "T+0"],
            "长线": ["长线", "价值", "持有", "配置"],
        }
        for tag, keywords in tag_keywords.items():
            if any(kw in query for kw in keywords):
                tags.append(tag)
        return tags if tags else ["general"]

    def _should_explore(self) -> bool:
        """15% exploration rate to avoid echo chambers."""
        import random
        return random.random() < 0.15
