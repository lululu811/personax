"""Orchestration Layer - Coordinates personas, tools, and signals.

Architecture:
    Query → Router → Tool Cache → Persona Analysis → Signal Aggregator → Response

Core components:
- Router: Determines which personas to involve based on query
- ToolCache: Caches computed tool results to avoid redundant computation
- SignalAggregator: Resolves conflicts when multiple personas give signals
- Engine: Main orchestration engine tying everything together
"""

from orchestration.router import Router
from orchestration.tool_cache import ToolCache
from orchestration.signal_aggregator import SignalAggregator
from orchestration.engine import OrchestrationEngine, OrchestrationRequest, OrchestrationResponse
from orchestration.response_generator import ResponseGenerator, GenerationContext
from orchestration.conversation import ConversationManager, ConversationState, DiagnosisEngine
from orchestration.models import StrategySignal

__all__ = [
    "Router",
    "ToolCache",
    "SignalAggregator",
    "OrchestrationEngine",
    "OrchestrationRequest",
    "OrchestrationResponse",
    "ResponseGenerator",
    "GenerationContext",
    "ConversationManager",
    "ConversationState",
    "DiagnosisEngine",
    "StrategySignal",
]
