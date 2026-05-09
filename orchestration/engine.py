"""Orchestration Engine - Main engine tying routing, caching, and aggregation."""

import re
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
from orchestration.response_generator import ResponseGenerator, GenerationContext
from orchestration.conversation import ConversationManager, ConversationState, DiagnosisEngine
from personas.persona_loader import load_persona
from tools.quant.technical import QUERY_TOOLS as _DEFAULT_QUERY_TOOLS
from tools.quant.technical.interface import get_tool as _get_tool
from tools.quant.technical.interface import list_tools as _list_tools
from tools.financial_reports import FinancialReportTool


@dataclass
class OrchestrationRequest:
    """A request to the orchestration engine."""
    query: str                          # User's natural language query
    df: Optional[pd.DataFrame] = None  # Stock data with OHLCV
    stock_code: Optional[str] = None   # Optional stock code
    persona_priority: list[str] = None  # Preferred personas (default: zettaranc)
    conflict_strategy: ConflictStrategy = ConflictStrategy.CONFIDENCE_WEIGHTED
    include_knowledge: bool = True      # Whether to query knowledge base
    conversation_id: Optional[str] = None  # For multi-turn conversation state


@dataclass
class OrchestrationResponse:
    """Response from the orchestration engine."""
    route: RouteResult
    tool_results: dict              # tool_name -> ToolResult
    strategy_results: dict           # strategy_name -> StrategySignal
    aggregated_signal: AggregatedSignal
    persona_analysis: str            # Analysis text from primary persona
    cached: bool                   # Whether results were from cache
    knowledge_snippets: list[str] = None  # Retrieved knowledge snippets
    conversation_id: str = None    # Conversation ID for multi-turn
    diagnosis_round: int = 0       # Current diagnosis round (0-3)
    diagnosis_pending: bool = False  # True if more diagnosis rounds needed
    diagnosis_route: Optional[str] = None  # A/B/C/D route letter




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
        self.response_generator = ResponseGenerator()
        self.conversation_manager = ConversationManager()
        self._strategy_cache = {}  # strategy_name -> strategy instance

    def execute(self, request: OrchestrationRequest) -> OrchestrationResponse:
        """Execute an orchestration request.

        Supports multi-turn diagnosis workflow:
          Round 0: New query -> start diagnosis or direct analysis
          Round 1: Asked cycle + status + position, awaiting answer
          Round 2: Asked path-specific questions, awaiting answer
          Round 3: Diagnosis complete -> full analysis

        Args:
            request: The orchestration request

        Returns:
            OrchestrationResponse with routing, tool results, and aggregated signal
        """
        # Step 0: Conversation state management
        state = self._get_or_create_state(request)
        state.add_history("user", request.query)

        # Check if we should enter/continue diagnosis flow
        should_diagnose = self._should_diagnose(request.query, state)
        if should_diagnose and state.diagnosis_round < 3:
            return self._handle_diagnosis(request, state)

        # Step 1: Route the query
        personas = request.persona_priority or ["zettaranc"]
        route = self.router.route(request.query, personas)

        # Step 2: Query knowledge base
        knowledge_snippets = []
        if request.include_knowledge:
            try:
                from knowledge.query import query_knowledge, format_results
                kb_results = query_knowledge(request.query, route.primary)
                formatted = format_results(kb_results)
                if formatted.strip():
                    knowledge_snippets = formatted.split("\n---\n")
                    knowledge_snippets = [s.strip() for s in knowledge_snippets if s.strip()]
            except Exception:
                # Knowledge base query is optional; don't fail the whole request
                knowledge_snippets = []

        # Step 3: Determine required tools and strategies
        tools_needed = self._get_tools_for_query(request.query)
        primary_persona = route.primary if 'route' in dir() else (request.persona_priority or ["zettaranc"])[0]
        strategies_needed = self._get_strategies_for_query(request.query, persona=primary_persona)

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

        # Step 7: Load persona config and generate persona-aware response
        try:
            persona_config = load_persona(route.primary)
        except Exception:
            persona_config = None

        if persona_config:
            analysis = self.response_generator.generate(
                query=request.query,
                persona_config=persona_config,
                context=GenerationContext(
                    knowledge_snippets=knowledge_snippets,
                    tool_results=tool_results,
                    strategy_results=strategy_results,
                    aggregated_signal=aggregated,
                    stock_code=request.stock_code,
                ),
            )
        else:
            # Fallback to template analysis
            analysis = self._build_analysis(route, tool_results, strategy_results)

        # Save conversation state
        state.add_history("assistant", analysis)
        self.conversation_manager.update_state(state.conversation_id, state)

        return OrchestrationResponse(
            route=route,
            tool_results=tool_results,
            strategy_results=strategy_results,
            aggregated_signal=aggregated,
            persona_analysis=analysis,
            cached=False,
            knowledge_snippets=knowledge_snippets if knowledge_snippets else None,
            conversation_id=state.conversation_id,
            diagnosis_round=state.diagnosis_round,
            diagnosis_pending=False,
            diagnosis_route=None,
        )

    def _get_tools_for_query(self, query: str) -> list[str]:
        """Determine which tools are needed for the query."""
        tools = set()
        query_lower = query.lower()

        for keyword, tool_list in _DEFAULT_QUERY_TOOLS.items():
            if keyword.lower() in query_lower:
                tools.update(tool_list)

        # Financial report keywords
        FINANCIAL_KEYWORDS = ["财报", "年报", "财务", "基本面"]
        for keyword in FINANCIAL_KEYWORDS:
            if keyword in query:
                tools.add("financial_reports")
                break

        # Always include kdj if no specific tool requested
        if not tools:
            tools.add("kdj")

        return list(tools)

    def _get_strategies_for_query(self, query: str, persona: str = "zettaranc") -> list[str]:
        """Determine which strategies to run for the query (persona-specific)."""
        strategies = set()
        query_lower = query.lower()

        # Dynamically load persona-specific query mappings
        query_mapping = self._load_strategy_keywords(persona)
        for keyword, strategy_list in query_mapping.items():
            if keyword.lower() in query_lower:
                strategies.update(strategy_list)

        return list(strategies)

    def _load_strategy_keywords(self, persona: str) -> dict:
        """Load keyword -> strategy mapping for a given persona."""
        # TODO: generalize for multiple personas; currently zettaranc is the reference
        if persona == "zettaranc":
            try:
                from personas.zettaranc.strategies import QUERY_STRATEGIES
                return QUERY_STRATEGIES
            except Exception:
                pass
        return {}

    def _compute_tool(self, tool_name: str, df: pd.DataFrame):
        """Compute a tool and return the result via registry."""
        if tool_name == "financial_reports":
            tool = FinancialReportTool()
            # FinancialReportTool expects a stock_code string, not a DataFrame
            # Return the tool instance for later use by response generator
            return tool
        tool_cls = _get_tool(tool_name)
        tool_instance = tool_cls()
        return tool_instance.compute(df)

    def _run_strategy(self, strategy_name: str, df: pd.DataFrame, tool_results: dict):
        """Run a strategy and return the signal via registry."""
        from personas.zettaranc.strategies import get_strategy

        # Use cached instance if available
        if strategy_name not in self._strategy_cache:
            self._strategy_cache[strategy_name] = get_strategy(strategy_name)

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

    # ------------------------------------------------------------------ #
    #  Multi-turn diagnosis helpers
    # ------------------------------------------------------------------ #

    def _get_or_create_state(self, request: OrchestrationRequest) -> ConversationState:
        """Restore existing conversation or create a new one."""
        if request.conversation_id:
            state = self.conversation_manager.get_state(request.conversation_id)
            if state:
                return state
        # New conversation
        cid = self.conversation_manager.create_conversation(
            persona=(request.persona_priority or ["zettaranc"])[0]
        )
        return self.conversation_manager.get_state(cid)

    def _should_diagnose(self, query: str, state: ConversationState) -> bool:
        """Determine if query should enter the diagnosis workflow.

        Triggers:
        - User asks about a specific stock (contains stock-like patterns)
        - User asks buy/sell/hold advice
        - Already in diagnosis flow (state.diagnosis_round > 0)
        """
        if state.diagnosis_round > 0:
            return True

        query_lower = query.lower()

        # Stock-related keywords that trigger diagnosis
        diagnose_keywords = [
            "怎么看", "能买吗", "能卖吗", "要不要买", "要不要卖",
            "持有", "建仓", "清仓", "减仓", "加仓", "被套", "浮盈", "浮亏",
            "短线", "长线", "止损", "止盈",
            "怎么样", "如何", "想", "该", "建议", "点评", "分析",
            "买", "卖", "入", "出", "操作",
        ]
        if any(kw in query_lower for kw in diagnose_keywords):
            return True

        # Stock code pattern (e.g., 600519, 300750, 000001)
        import re
        if re.search(r"\b\d{6}\b", query):
            return True

        return False

    def _handle_diagnosis(
        self,
        request: OrchestrationRequest,
        state: ConversationState,
    ) -> OrchestrationResponse:
        """Handle multi-turn diagnosis flow.

        Round 0 -> 1: Ask cycle + status + position
        Round 1 -> 2: Ask route-specific questions
        Round 2 -> 3: Generate diagnosis conclusion
        """
        if state.diagnosis_round == 0:
            return self._diagnosis_round1(request, state)
        elif state.diagnosis_round == 1:
            return self._diagnosis_round2(request, state)
        elif state.diagnosis_round == 2:
            return self._diagnosis_round3(request, state)

        # Fallback — should not reach here
        return self._diagnosis_round3(request, state)

    def _diagnosis_round1(
        self,
        request: OrchestrationRequest,
        state: ConversationState,
    ) -> OrchestrationResponse:
        """Start diagnosis: ask cycle + status + position."""
        # Still compute tools/strategies for context
        personas = request.persona_priority or ["zettaranc"]
        route = self.router.route(request.query, personas)

        tools_needed = self._get_tools_for_query(request.query)
        strategies_needed = self._get_strategies_for_query(request.query)

        tool_results = {}
        strategy_results = {}
        if request.df is not None:
            df_hash = self.tool_cache.hash_dataframe(request.df)
            for tool_name in tools_needed:
                cached = self.tool_cache.get(tool_name, df_hash)
                if cached is not None:
                    tool_results[tool_name] = cached
                else:
                    result = self._compute_tool(tool_name, request.df)
                    tool_results[tool_name] = result
                    self.tool_cache.set(tool_name, df_hash, result)

            for strategy_name in strategies_needed:
                signal = self._run_strategy(strategy_name, request.df, tool_results)
                strategy_results[strategy_name] = signal

        # Knowledge query
        knowledge_snippets = []
        if request.include_knowledge:
            try:
                from knowledge.query import query_knowledge, format_results
                kb_results = query_knowledge(request.query, route.primary)
                formatted = format_results(kb_results)
                if formatted.strip():
                    knowledge_snippets = formatted.split("\n---\n")
                    knowledge_snippets = [s.strip() for s in knowledge_snippets if s.strip()]
            except Exception:
                knowledge_snippets = []

        # Advance state
        state.advance_round()  # 0 -> 1
        self.conversation_manager.update_state(state.conversation_id, state)

        # Build round-1 questions
        questions = DiagnosisEngine.get_round1_questions()
        analysis = self.response_generator.generate_diagnosis_round1(
            query=request.query,
            route=route,
            tool_results=tool_results,
            strategy_results=strategy_results,
            questions=questions,
        )

        return OrchestrationResponse(
            route=route,
            tool_results=tool_results,
            strategy_results=strategy_results,
            aggregated_signal=AggregatedSignal(
                action="hold", confidence=0.0, reasons=["Diagnosis in progress"],
                conflict_detected=False, resolution_strategy="none", persona_signals=[],
            ),
            persona_analysis=analysis,
            cached=False,
            knowledge_snippets=knowledge_snippets if knowledge_snippets else None,
            conversation_id=state.conversation_id,
            diagnosis_round=1,
            diagnosis_pending=True,
            diagnosis_route=None,
        )

    def _diagnosis_round2(
        self,
        request: OrchestrationRequest,
        state: ConversationState,
    ) -> OrchestrationResponse:
        """Process round-1 answers and ask route-specific questions."""
        # Parse round-1 answer from query
        parsed = self._parse_round1_answer(request.query)
        state.add_answer(1, parsed)

        # Determine route
        route_letter = DiagnosisEngine.determine_route(
            parsed.get("cycle", ""), parsed.get("status", "")
        )
        if route_letter:
            state.set_route(route_letter)

        # Position alert
        alert_triggered, alert_msg = DiagnosisEngine.check_position_alert(
            parsed.get("position", "")
        )

        # Advance state
        state.advance_round()  # 1 -> 2
        self.conversation_manager.update_state(state.conversation_id, state)

        # Build round-2 questions
        route_label = DiagnosisEngine.ROUTES.get(route_letter, "进一步确认")
        questions = DiagnosisEngine.get_round2_questions(route_letter or "A")
        analysis = self.response_generator.generate_diagnosis_round2(
            query=request.query,
            state=state,
            route_letter=route_letter,
            route_label=route_label,
            questions=questions,
            alert_msg=alert_msg if alert_triggered else "",
        )

        return OrchestrationResponse(
            route=RouteResult(
                primary=state.persona, secondary=[], intent="diagnosis",
                confidence=0.9, reasoning=f"Round 2: {route_label}"
            ),
            tool_results={},
            strategy_results={},
            aggregated_signal=AggregatedSignal(
                action="hold", confidence=0.0, reasons=["Diagnosis in progress"],
                conflict_detected=False, resolution_strategy="none", persona_signals=[],
            ),
            persona_analysis=analysis,
            cached=False,
            conversation_id=state.conversation_id,
            diagnosis_round=2,
            diagnosis_pending=True,
            diagnosis_route=route_letter,
        )

    def _diagnosis_round3(
        self,
        request: OrchestrationRequest,
        state: ConversationState,
    ) -> OrchestrationResponse:
        """Process round-2 answers and generate diagnosis conclusion."""
        # Parse round-2 answer from query
        parsed = self._parse_round2_answer(request.query, state.diagnosis_route)
        state.add_answer(2, parsed)

        # Re-compute tools/strategies with full context
        personas = request.persona_priority or ["zettaranc"]
        route = self.router.route(request.query, personas)

        tools_needed = self._get_tools_for_query(request.query)
        strategies_needed = self._get_strategies_for_query(request.query)

        tool_results = {}
        strategy_results = {}
        if request.df is not None:
            df_hash = self.tool_cache.hash_dataframe(request.df)
            for tool_name in tools_needed:
                cached = self.tool_cache.get(tool_name, df_hash)
                if cached is not None:
                    tool_results[tool_name] = cached
                else:
                    result = self._compute_tool(tool_name, request.df)
                    tool_results[tool_name] = result
                    self.tool_cache.set(tool_name, df_hash, result)

            for strategy_name in strategies_needed:
                signal = self._run_strategy(strategy_name, request.df, tool_results)
                strategy_results[strategy_name] = signal

        # Aggregate signals
        persona_signals = []
        if request.persona_priority and "zettaranc" in request.persona_priority:
            for name, signal in strategy_results.items():
                if signal.action != "hold":
                    persona_signals.append(PersonaSignal(
                        persona="zettaranc",
                        action=signal.action,
                        confidence=signal.confidence,
                        reason=signal.reason,
                        metadata=signal.metadata,
                    ))

        self.signal_aggregator.strategy = request.conflict_strategy
        aggregated = self.signal_aggregator.aggregate(persona_signals)

        # Knowledge query
        knowledge_snippets = []
        if request.include_knowledge:
            try:
                from knowledge.query import query_knowledge, format_results
                kb_results = query_knowledge(request.query, route.primary)
                formatted = format_results(kb_results)
                if formatted.strip():
                    knowledge_snippets = formatted.split("\n---\n")
                    knowledge_snippets = [s.strip() for s in knowledge_snippets if s.strip()]
            except Exception:
                knowledge_snippets = []

        # Generate rule-based diagnosis helper text
        diagnosis_helper = DiagnosisEngine.generate_diagnosis(
            state.diagnosis_route or "A", state.answers, strategy_results
        )

        # Generate persona-aware conclusion
        try:
            persona_config = load_persona(route.primary)
        except Exception:
            persona_config = None

        if persona_config:
            analysis = self.response_generator.generate_diagnosis_conclusion(
                query=request.query,
                persona_config=persona_config,
                state=state,
                context=GenerationContext(
                    knowledge_snippets=knowledge_snippets,
                    tool_results=tool_results,
                    strategy_results=strategy_results,
                    aggregated_signal=aggregated,
                    stock_code=request.stock_code,
                ),
                diagnosis_helper=diagnosis_helper,
                history=state.get_recent_history(),
            )
        else:
            analysis = diagnosis_helper

        # Advance state and save
        state.advance_round()  # 2 -> 3
        state.add_history("assistant", analysis)
        self.conversation_manager.update_state(state.conversation_id, state)

        return OrchestrationResponse(
            route=route,
            tool_results=tool_results,
            strategy_results=strategy_results,
            aggregated_signal=aggregated,
            persona_analysis=analysis,
            cached=False,
            knowledge_snippets=knowledge_snippets if knowledge_snippets else None,
            conversation_id=state.conversation_id,
            diagnosis_round=3,
            diagnosis_pending=False,
            diagnosis_route=state.diagnosis_route,
        )

    def _parse_round1_answer(self, query: str) -> dict:
        """Extract cycle, status, position from user's round-1 answer.

        Simple rule-based parsing. Can be enhanced with LLM.
        """
        query_lower = query.lower()
        result = {"cycle": "", "status": "", "position": ""}

        # Cycle
        if "短线" in query or "短" in query:
            result["cycle"] = "短线"
        elif "长线" in query or "长" in query or "价值" in query:
            result["cycle"] = "长线"
        elif "不确定" in query or "不知道" in query:
            result["cycle"] = "不确定"

        # Status
        if any(kw in query for kw in ["已持有", "持有", "买了", "持仓", "被套", "浮盈", "浮亏"]):
            result["status"] = "已持有"
        elif any(kw in query for kw in ["想进场", "想买", "建仓", "买入", "能买吗", "进场"]):
            result["status"] = "想进场"
        elif any(kw in query for kw in ["想卖出", "想卖", "减仓", "清仓", "卖出", "能卖吗"]):
            result["status"] = "想卖出"
        elif "不确定" in query or "不知道" in query:
            result["status"] = "不确定"

        # Position — try to extract percentage
        pct_match = re.search(r"(\d+)%?", query)
        if pct_match:
            result["position"] = f"{pct_match.group(1)}%"
        if any(kw in query for kw in ["满仓", "全仓", "梭哈", "all in"]):
            result["position"] = "满仓"
        elif any(kw in query for kw in ["没买", "空仓", "还没", "0"]):
            result["position"] = "0%"

        return result

    def _parse_round2_answer(self, query: str, route: Optional[str]) -> dict:
        """Extract path-specific answers from round-2 response."""
        query_lower = query.lower()
        result = {}

        if route == "A":  # 持仓诊断
            # Cost price
            cost_match = re.search(r"成本[价]*[\s:：]*(\d+\.?\d*)", query)
            if cost_match:
                result["cost"] = cost_match.group(1)
            # PnL
            if "浮盈" in query or "赚" in query:
                result["pnl"] = "浮盈"
            elif "浮亏" in query or "亏" in query or "套" in query:
                result["pnl"] = "浮盈转浮亏"
            # Signal
            if "B1" in query:
                result["signal"] = "B1"
            elif "B2" in query:
                result["signal"] = "B2"
            elif "砖" in query:
                result["signal"] = "砖形图"
            elif "感觉" in query or "凭感觉" in query:
                result["signal"] = "凭感觉"
            # Days
            day_match = re.search(r"(\d+)\s*天", query)
            if day_match:
                result["days"] = day_match.group(1)

        elif route == "B":  # 买点确认
            # J value
            j_match = re.search(r"J\s*[值]*[\s:：]*(-?\d+\.?\d*)", query)
            if j_match:
                result["j_value"] = j_match.group(1)
            # Brick color
            if "绿" in query or "绿色" in query:
                result["brick"] = "绿砖"
            elif "红" in query or "红色" in query:
                result["brick"] = "红砖"
            # Market status
            if "-2.3" in query or "负" in query:
                result["market"] = "-2.3%"
            elif "+4" in query or "正" in query:
                result["market"] = "+4%"
            # Heard from others
            if "听" in query or "别人" in query or "推荐" in query:
                result["heard"] = "听别人说的"
            else:
                result["heard"] = "自己分析的"

        elif route == "C":  # 逃命判断
            # Reason
            if "止损" in query or "跌破" in query:
                result["reason"] = "跌破止损线"
            elif "慌" in query or "怕" in query:
                result["reason"] = "心里慌"
            elif "无利空" in query or "暴跌" in query:
                result["reason"] = "无利空暴跌"
            # Stop level
            if "最低价" in query:
                result["stop"] = "买入当日最低价"
            elif "BBI" in query:
                result["stop"] = "BBI"
            # Close broke
            if "收盘" in query and "跌破" in query:
                result["close_broke"] = "收盘价跌破"
                if "连续两天" in query or "两天" in query:
                    result["close_broke"] += " 连续两天"
            elif "盘中" in query:
                result["close_broke"] = "盘中跌破"

        elif route == "D":  # 长线配置
            # Scarcity
            if any(kw in query for kw in ["是", "稀缺", "龙头", "茅台", "腾讯", "比亚迪"]):
                result["scarcity"] = "是稀缺资产"
            elif any(kw in query for kw in ["不是", "否", "没有", "一般"]):
                result["scarcity"] = "不是稀缺资产"
            # Idle money
            if any(kw in query for kw in ["闲钱", "不急", "是"]):
                result["idle_money"] = "是闲钱"
            elif any(kw in query for kw in ["急用", "生活费", "不是", "否"]):
                result["idle_money"] = "不是闲钱"
            # Cycle position
            if "起步" in query or "早期" in query:
                result["cycle_pos"] = "起步期"
            elif "加速" in query or "成长" in query:
                result["cycle_pos"] = "加速期"
            elif "人人都知道" in query or "末期" in query or "成熟" in query:
                result["cycle_pos"] = "人人都知道能赚钱了"

        return result
