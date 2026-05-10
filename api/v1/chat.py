from fastapi import APIRouter, Depends
from pydantic import BaseModel
from api.auth.dependencies import get_current_user
from api.auth.models import User

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    stock_code: str | None = None
    persona: str = "zettaranc"
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    persona_analysis: str
    route: dict
    tool_results: dict = {}
    strategy_results: dict = {}
    aggregated_signal: dict = {}
    conversation_id: str | None = None


_engine = None


def get_engine():
    global _engine
    if _engine is None:
        from orchestration.engine import OrchestrationEngine
        _engine = OrchestrationEngine()
    return _engine


@router.post("", response_model=ChatResponse)
async def chat(data: ChatRequest, user: User = Depends(get_current_user)):
    from orchestration.engine import OrchestrationRequest

    engine = get_engine()

    df = None
    if data.stock_code:
        try:
            from data.db import Database
            db = Database()
            df = db.get_daily(data.stock_code)
        except Exception:
            pass

    request = OrchestrationRequest(
        query=data.query,
        df=df,
        stock_code=data.stock_code,
        persona_priority=[data.persona],
        conversation_id=data.conversation_id,
    )

    response = engine.execute(request)

    return ChatResponse(
        persona_analysis=response.persona_analysis,
        route={
            "primary": response.route.primary,
            "intent": response.route.intent,
            "confidence": response.route.confidence,
        },
        tool_results={k: str(v) for k, v in response.tool_results.items()},
        strategy_results={k: {
            "action": v.action,
            "confidence": v.confidence,
            "reason": v.reason,
        } for k, v in response.strategy_results.items()},
        aggregated_signal={
            "action": response.aggregated_signal.action,
            "confidence": response.aggregated_signal.confidence,
        },
        conversation_id=response.conversation_id,
    )
