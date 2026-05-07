"""Orchestration Engine - Main engine tying routing, caching, and aggregation."""

from dataclasses import dataclass
from typing import Optional

from orchestration.router import Router, RouteResult
from orchestration.tool_cache import ToolCache
from orchestration.signal_aggregator import (
    SignalAggregator,
    ConflictStrategy,
    PersonaSignal,
    AggregatedSignal,
)


@dataclass
class OrchestrationRequest:
    """A request to the orchestration engine."""
    query: str                          # User's natural language query
    stock_code: Optional[str] = None   # Optional stock code to analyze
    persona_priority: list[str] = None  # Preferred personas (default: zettaranc)
    conflict_strategy: ConflictStrategy = ConflictStrategy.CONFIDENCE_WEIGHTED


@dataclass
class OrchestrationResponse:
    """Response from the orchestration engine."""
    route: RouteResult
    tool_results: dict                  # tool_name -> ToolResult
    aggregated_signal: AggregatedSignal
    persona_analyses: dict             # persona -> analysis text
    cached: bool                        # Whether results were from cache


class OrchestrationEngine:
    """Main orchestration engine.

    Coordinates:
    1. Router - determines which personas to involve
    2. ToolCache - caches and reuses tool computations
    3. SignalAggregator - resolves conflicts between personas

    Usage:
        engine = OrchestrationEngine()
        response = engine.execute(OrchestrationRequest(
            query="帮我看看这只票，B1信号怎么看",
            stock_code="000001.SZ",
        ))
        print(response.aggregated_signal.action)
    """

    def __init__(self):
        self.router = Router()
        self.tool_cache = ToolCache()
        self.signal_aggregator = SignalAggregator()

    def execute(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Execute an orchestration request.

        Args:
            request: The orchestration request

        Returns:
            OrchestrationResponse with routing, tool results, and aggregated signal
        """
        # Step 1: Route the query
        personas = request.persona_priority or ["zettaranc"]
        route = self.router.route(request.query, personas)

        # Step 2: Compute tools (with caching)
        # TODO: Actually compute tools here once tools are wired up
        tool_results = {}

        # Step 3: Aggregate signals
        aggregated = self.signal_aggregator.aggregate([])

        return OrchestrationResponse(
            route=route,
            tool_results=tool_results,
            aggregated_signal=aggregated,
            persona_analyses={},
            cached=False,
        )

    def add_tool_result(self, tool_name: str, result) -> None:
        """Add a tool result to the cache.

        This will be called by personas when they compute tools.
        """
        # Tool results are cached by the tool cache directly
        pass
