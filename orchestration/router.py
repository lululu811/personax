"""Router - Determines which personas to involve based on query."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class RouteResult:
    """Result of routing a query to personas."""
    primary: str                    # Primary persona name
    secondary: list[str]             # Secondary personas to involve
    intent: str                      # Classified intent
    confidence: float                # Routing confidence
    reasoning: str                  # Why this routing was chosen


class Router:
    """Routes queries to appropriate personas.

    Simple keyword-based routing for now.
    Can be extended with LLM-based intent classification.
    """

    # Keyword → persona mapping
    KEYWORD_PERSONAS = {
        "技术": "zettaranc",
        "指标": "zettaranc",
        "B1": "zettaranc",
        "B2": "zettaranc",
        "KDJ": "zettaranc",
        "RSI": "zettaranc",
        "量": "zettaranc",
        "估值": "munger",
        "ROE": "munger",
        "营收": "munger",
        "利润": "munger",
        "基本面": "munger",
        "宏观": "boss_mo",
        "政策": "boss_mo",
        "利率": "boss_mo",
        "GDP": "boss_mo",
    }

    # Intent keywords
    INTENT_KEYWORDS = {
        "analyze": ["分析", "看看", "怎么看", "判断"],
        "buy": ["买", "买入", "建仓", "买入"],
        "sell": ["卖", "卖出", "减仓", "清仓"],
        "compare": ["对比", "比较", "哪个好"],
        "screen": ["选股", "筛选", "找"],
    }

    def route(self, query: str, available_personas: list[str]) -> RouteResult:
        """Route a query to appropriate personas.

        Args:
            query: The user's natural language query
            available_personas: List of available persona names

        Returns:
            RouteResult with primary/secondary personas and classified intent
        """
        query_lower = query.lower()

        # Determine primary persona based on keywords
        primary = self._find_primary(query_lower, available_personas)

        # Determine if secondary personas needed
        secondary = self._find_secondary(query_lower, available_personas, primary)

        # Classify intent
        intent = self._classify_intent(query_lower)

        return RouteResult(
            primary=primary,
            secondary=secondary,
            intent=intent,
            confidence=0.8,  # TODO: implement confidence scoring
            reasoning=f"Primary={primary}, intent={intent}",
        )

    def _find_primary(self, query: str, personas: list[str]) -> str:
        """Find the primary persona based on keywords."""
        for keyword, persona in self.KEYWORD_PERSONAS.items():
            if keyword in query and persona in personas:
                return persona

        # Default to zettaranc for quant queries
        if "zettaranc" in personas:
            return "zettaranc"

        # Fallback to first available
        return personas[0] if personas else "unknown"

    def _find_secondary(
        self, query: str, personas: list[str], primary: str
    ) -> list[str]:
        """Find secondary personas that should be involved."""
        secondary = []

        # Check for multi-persona keywords
        if any(k in query for k in ["估值", "基本面"]) and "munger" in personas:
            secondary.append("munger")
        if any(k in query for k in ["宏观", "政策"]) and "boss_mo" in personas:
            secondary.append("boss_mo")

        # If asking for comparison, involve both
        if "对比" in query or "比较" in query:
            for p in personas:
                if p != primary and p not in secondary:
                    secondary.append(p)

        return secondary

    def _classify_intent(self, query: str) -> str:
        """Classify the intent of the query."""
        for intent, keywords in self.INTENT_KEYWORDS.items():
            if any(k in query for k in keywords):
                return intent
        return "analyze"  # Default intent
