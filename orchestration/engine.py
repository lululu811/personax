"""Orchestration Engine - Main engine tying routing, caching, and aggregation."""

from dataclasses import dataclass, field
from typing import Optional, Any
import pandas as pd

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
    df: Optional[pd.DataFrame] = None  # Stock data with OHLCV
    stock_code: Optional[str] = None   # Optional stock code
    persona_priority: list[str] = None  # Preferred personas (default: zettaranc)
    conflict_strategy: ConflictStrategy = ConflictStrategy.CONFIDENCE_WEIGHTED


@dataclass
class OrchestrationResponse:
    """Response from the orchestration engine."""
    route: RouteResult
    tool_results: dict              # tool_name -> ToolResult
    strategy_results: dict           # strategy_name -> StrategySignal
    aggregated_signal: AggregatedSignal
    persona_analysis: str            # Analysis text from primary persona
    cached: bool                   # Whether results were from cache


# Query -> Tool mapping
QUERY_TOOLS = {
    "kdj": ["kdj"],
    "rsi": ["rsi_3"],
    "bbi": ["bbi"],
    "macd": ["macd"],
    "布林": ["bollinger"],
    "atr": ["atr"],
    "随机": ["stochastic"],
}

# Query -> Strategy mapping
QUERY_STRATEGIES = {
    "B1": ["b1"],
    "b1": ["b1"],
    "B2": ["b2_break"],
    "b2": ["b2_break"],
    "五分": ["five_score"],
    "五点": ["five_score"],
    "sb1": ["sb1"],
    "S1": ["s1_warning"],
    "s1": ["s1_warning"],
    "半仓": ["half_release"],
    "终极B1": ["ultimate_b1"],
    "超级B1": ["super_b1"],
    "单针": ["single_needle_20"],
    "补票": ["single_needle_20"],
    "异动": ["abnormal"],
    "坑口": ["pit_target"],
    "三波": ["three_waves"],
    "两个30": ["two_thirty"],
    "双马尾": ["double_ponytail"],
    "三外有三": ["three_outside_three"],
    "大风车": ["top_windmill"],
    "四分之三": ["three_quarters_volume"],
    "假阴": ["fake_bearish"],
    "双枪": ["double_gun"],
    "买盘枯竭": ["buy_exhaustion"],
    "长阴短柱": ["long_shadow_short_volume"],
}


class OrchestrationEngine:
    """Main orchestration engine.

    Coordinates:
    1. Router - determines which personas to involve
    2. ToolCache - caches and reuses tool computations
    3. SignalAggregator - resolves conflicts between personas

    Usage:
        engine = OrchestrationEngine()
        response = engine.execute(OrchestrationRequest(
            query="帮我看看B1信号",
            df=stock_data,
        ))
        print(response.aggregated_signal.action)
    """

    def __init__(self):
        self.router = Router()
        self.tool_cache = ToolCache()
        self.signal_aggregator = SignalAggregator()
        self._strategy_cache = {}  # strategy_name -> strategy instance

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

        # Step 2: Determine required tools and strategies
        tools_needed = self._get_tools_for_query(request.query)
        strategies_needed = self._get_strategies_for_query(request.query)

        # Step 3: Compute tools with caching
        tool_results = {}
        if request.df is not None:
            df_hash = self.tool_cache.hash_dataframe(request.df)

            for tool_name in tools_needed:
                cached = self.tool_cache.get(tool_name, df_hash)
                if cached is not None:
                    tool_results[tool_name] = cached
                else:
                    # Compute tool
                    tool_result = self._compute_tool(tool_name, request.df)
                    tool_results[tool_name] = tool_result
                    self.tool_cache.set(tool_name, df_hash, tool_result)

        # Step 4: Run strategies
        strategy_results = {}
        if request.df is not None:
            for strategy_name in strategies_needed:
                strategy_signal = self._run_strategy(strategy_name, request.df, tool_results)
                strategy_results[strategy_name] = strategy_signal

        # Step 5: Build persona signals for aggregation
        persona_signals = []
        if request.persona_priority and "zettaranc" in request.persona_priority:
            # Convert strategy results to PersonaSignal
            for name, signal in strategy_results.items():
                if signal.action != "hold":
                    persona_signals.append(PersonaSignal(
                        persona="zettaranc",
                        action=signal.action,
                        confidence=signal.confidence,
                        reason=signal.reason,
                        metadata=signal.metadata,
                    ))

        # Step 6: Aggregate signals
        self.signal_aggregator.strategy = request.conflict_strategy
        aggregated = self.signal_aggregator.aggregate(persona_signals)

        # Step 7: Build analysis text
        analysis = self._build_analysis(route, tool_results, strategy_results)

        return OrchestrationResponse(
            route=route,
            tool_results=tool_results,
            strategy_results=strategy_results,
            aggregated_signal=aggregated,
            persona_analysis=analysis,
            cached=False,
        )

    def _get_tools_for_query(self, query: str) -> list[str]:
        """Determine which tools are needed for the query."""
        tools = set()
        query_lower = query.lower()

        for keyword, tool_list in QUERY_TOOLS.items():
            if keyword.lower() in query_lower:
                tools.update(tool_list)

        # Always include kdj if strategies need it
        if not tools:
            tools.add("kdj")

        return list(tools)

    def _get_strategies_for_query(self, query: str) -> list[str]:
        """Determine which strategies to run for the query."""
        strategies = set()
        query_lower = query.lower()

        for keyword, strategy_list in QUERY_STRATEGIES.items():
            if keyword.lower() in query_lower:
                strategies.update(strategy_list)

        return list(strategies)

    def _compute_tool(self, tool_name: str, df: pd.DataFrame):
        """Compute a tool and return the result."""
        from tools.quant.technical import kdj, rsi_3, bbi, stochastic, macd, bollinger, atr

        TOOL_MAP = {
            "kdj": kdj,
            "rsi_3": rsi_3,
            "bbi": bbi,
            "stochastic": stochastic,
            "macd": macd,
            "bollinger": bollinger,
            "atr": atr,
        }

        tool = TOOL_MAP.get(tool_name)
        if tool is None:
            raise ValueError(f"Unknown tool: {tool_name}")

        return tool.compute(df)

    def _run_strategy(self, strategy_name: str, df: pd.DataFrame, tool_results: dict):
        """Run a strategy and return the signal."""
        from personas.zettaranc.strategies import (
            B1Strategy, B2BreakStrategy, FiveScoreStrategy,
            SB1FakeFallStrategy, S1WarningStrategy, HalfReleaseStrategy,
            UltimateB1Strategy, SuperB1Strategy, SingleNeedle20Strategy,
            AbnormalMovementStrategy, PitTargetStrategy, ThreeWavesStrategy,
            TwoThirtyRuleStrategy, DoublePonytailStrategy, ThreeOutsideThreeStrategy,
            TopWindmillStrategy, ThreeQuartersVolumeStrategy, FakeBearishStrategy,
            DoubleGunStrategy, BuyExhaustionStrategy, LongShadowShortVolumeStrategy,
        )

        STRATEGY_MAP = {
            "b1": B1Strategy,
            "b2_break": B2BreakStrategy,
            "five_score": FiveScoreStrategy,
            "sb1": SB1FakeFallStrategy,
            "s1_warning": S1WarningStrategy,
            "half_release": HalfReleaseStrategy,
            "ultimate_b1": UltimateB1Strategy,
            "super_b1": SuperB1Strategy,
            "single_needle_20": SingleNeedle20Strategy,
            "abnormal": AbnormalMovementStrategy,
            "pit_target": PitTargetStrategy,
            "three_waves": ThreeWavesStrategy,
            "two_thirty": TwoThirtyRuleStrategy,
            "double_ponytail": DoublePonytailStrategy,
            "three_outside_three": ThreeOutsideThreeStrategy,
            "top_windmill": TopWindmillStrategy,
            "three_quarters_volume": ThreeQuartersVolumeStrategy,
            "fake_bearish": FakeBearishStrategy,
            "double_gun": DoubleGunStrategy,
            "buy_exhaustion": BuyExhaustionStrategy,
            "long_shadow_short_volume": LongShadowShortVolumeStrategy,
        }

        strategy_class = STRATEGY_MAP.get(strategy_name)
        if strategy_class is None:
            raise ValueError(f"Unknown strategy: {strategy_name}")

        # Use cached instance if available
        if strategy_name not in self._strategy_cache:
            self._strategy_cache[strategy_name] = strategy_class()

        strategy = self._strategy_cache[strategy_name]
        return strategy.detect(df)

    def _build_analysis(
        self,
        route: RouteResult,
        tool_results: dict,
        strategy_results: dict,
    ) -> str:
        """Build human-readable analysis text."""
        lines = [f"路由: {route.primary} ({route.intent})"]

        # Tool results summary
        for name, result in tool_results.items():
            if hasattr(result, 'data'):
                last_values = {k: f"{v.iloc[-1]:.2f}" if hasattr(v, 'iloc') else v
                              for k, v in result.data.items()}
                lines.append(f"工具[{name}]: {last_values}")

        # Strategy results
        for name, signal in strategy_results.items():
            if signal.action != "hold":
                lines.append(f"策略[{name}]: {signal.action} ({signal.confidence:.0%}) - {signal.reason}")

        return "\n".join(lines)
