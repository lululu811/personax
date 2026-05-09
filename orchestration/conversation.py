"""Conversation Manager - Multi-turn dialogue state for persona diagnosis.

Manages the 3-round diagnosis workflow defined in SKILL.md:
  Round 1: Cycle (short/long) + Position status + Position size
  Round 2: Path-specific questions (A/B/C/D)
  Round 3: Diagnosis conclusion

Usage:
    from orchestration.conversation import ConversationManager, ConversationState

    cm = ConversationManager()
    cid = cm.create_conversation(persona="zettaranc")
    state = cm.get_state(cid)
    state.add_answer("短线", "已持有", "30%")
    state.route = "A"  # 持仓诊断
    cm.update_state(cid, state)
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime


@dataclass
class ConversationState:
    """Mutable state for a single conversation."""

    conversation_id: str
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)

    # Diagnosis flow
    persona: str = "zettaranc"
    diagnosis_round: int = 0          # 0=initial, 1=first, 2=second, 3=conclusion
    diagnosis_route: Optional[str] = None   # "A"/"B"/"C"/"D"/None

    # Accumulated user answers (round -> dict of answers)
    answers: dict[int, dict] = field(default_factory=dict)

    # Extracted context (stock_code, cost_price, position_pct, etc.)
    context: dict[str, Any] = field(default_factory=dict)

    # Last signal results (for continuity across turns)
    last_signals: dict = field(default_factory=dict)

    # Conversation history for LLM context
    history: list[dict] = field(default_factory=list)

    def add_answer(self, round_num: int, answer: dict):
        """Add user answers for a given round."""
        self.answers[round_num] = answer
        self.last_active = time.time()

    def add_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.history.append({"role": role, "content": content, "timestamp": time.time()})
        self.last_active = time.time()

    def advance_round(self):
        """Advance to the next diagnosis round."""
        self.diagnosis_round += 1
        self.last_active = time.time()

    def set_route(self, route: str):
        """Set the diagnosis route (A/B/C/D)."""
        self.diagnosis_route = route
        self.last_active = time.time()

    def set_context(self, key: str, value: Any):
        """Set a context value."""
        self.context[key] = value
        self.last_active = time.time()

    def is_expired(self, ttl_seconds: float = 1800.0) -> bool:
        """Check if conversation has expired (default 30 min)."""
        return time.time() - self.last_active > ttl_seconds

    def get_recent_history(self, n: int = 6) -> list[dict]:
        """Get last n messages for LLM context (without timestamps)."""
        recent = self.history[-n:]
        return [{"role": m["role"], "content": m["content"]} for m in recent]

    def to_dict(self) -> dict:
        """Serialize state to dict."""
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "last_active": self.last_active,
            "persona": self.persona,
            "diagnosis_round": self.diagnosis_round,
            "diagnosis_route": self.diagnosis_route,
            "answers": self.answers,
            "context": self.context,
            "last_signals": self.last_signals,
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationState":
        """Deserialize from dict."""
        return cls(
            conversation_id=data["conversation_id"],
            created_at=data.get("created_at", time.time()),
            last_active=data.get("last_active", time.time()),
            persona=data.get("persona", "zettaranc"),
            diagnosis_round=data.get("diagnosis_round", 0),
            diagnosis_route=data.get("diagnosis_route"),
            answers=data.get("answers", {}),
            context=data.get("context", {}),
            last_signals=data.get("last_signals", {}),
            history=data.get("history", []),
        )


class ConversationManager:
    """Manages conversation states in memory with TTL cleanup.

    Usage:
        cm = ConversationManager(ttl_seconds=1800)
        cid = cm.create_conversation("zettaranc")
        state = cm.get_state(cid)
        # ... interact ...
        cm.update_state(cid, state)
    """

    def __init__(self, ttl_seconds: float = 1800.0):
        self._states: dict[str, ConversationState] = {}
        self._ttl = ttl_seconds

    def create_conversation(self, persona: str = "zettaranc") -> str:
        """Create a new conversation and return its ID."""
        cid = str(uuid.uuid4())[:12]
        self._states[cid] = ConversationState(
            conversation_id=cid,
            persona=persona,
        )
        return cid

    def get_state(self, conversation_id: str) -> Optional[ConversationState]:
        """Get conversation state by ID. Returns None if expired/not found."""
        self._cleanup_expired()
        state = self._states.get(conversation_id)
        if state and state.is_expired(self._ttl):
            del self._states[conversation_id]
            return None
        return state

    def update_state(self, conversation_id: str, state: ConversationState):
        """Update conversation state."""
        state.last_active = time.time()
        self._states[conversation_id] = state

    def delete_conversation(self, conversation_id: str):
        """Delete a conversation."""
        self._states.pop(conversation_id, None)

    def list_active(self) -> list[str]:
        """List all active conversation IDs."""
        self._cleanup_expired()
        return list(self._states.keys())

    def _cleanup_expired(self):
        """Remove expired conversations."""
        now = time.time()
        expired = [
            cid for cid, s in self._states.items()
            if now - s.last_active > self._ttl
        ]
        for cid in expired:
            del self._states[cid]


class DiagnosisEngine:
    """Determines diagnosis route and next questions based on user answers.

    Implements the 4-path routing logic from SKILL.md Step 1.5.
    """

    # Route definitions
    ROUTES = {
        "A": "持仓诊断",    # 短线 + 已持有
        "B": "买点确认",    # 短线 + 想进场
        "C": "逃命判断",    # 短线 + 想卖出
        "D": "长线配置",    # 长线
    }

    @classmethod
    def determine_route(cls, cycle: str, status: str) -> Optional[str]:
        """Determine diagnosis route from cycle + status.

        Args:
            cycle: "短线" | "长线" | "不确定"
            status: "已持有" | "想进场" | "想卖出" | "不确定"

        Returns:
            Route letter (A/B/C/D) or None if insufficient info
        """
        cycle = cycle.strip() if cycle else ""
        status = status.strip() if status else ""

        if cycle == "长线":
            return "D"

        if cycle == "短线":
            if status == "已持有":
                return "A"
            if status == "想进场":
                return "B"
            if status == "想卖出":
                return "C"

        return None

    @classmethod
    def get_round1_questions(cls) -> list[str]:
        """Get first round questions (must ask all three)."""
        return [
            "你是做短线还是长线？不一样的。",
            "你现在是已经持有了，还是在看想进场？",
            "这只票你占了多少仓位？还是还没买？",
        ]

    @classmethod
    def get_round2_questions(cls, route: str) -> list[str]:
        """Get second round questions based on route."""
        questions = {
            "A": [  # 持仓诊断
                "你的成本价多少？现在浮盈还是浮亏？",
                "你是看到什么信号买的？B1？四块砖？还是凭感觉？",
                "买了几天了？中间有没有创新高/新低？",
            ],
            "B": [  # 买点确认
                "你看到什么信号了？J 值打到多少了？砖形图是红是绿？",
                "现在是主线票还是主题票？政策支不支持？",
                "今天的量比是多少？活跃市值是 +4% 还是 -2.3%？",
                "你自己分析的还是听别人说的？",
            ],
            "C": [  # 逃命判断
                "为什么想卖？跌破止损线了，还是心里慌？",
                "你的止损设在哪？买入当日最低价？还是 BBI？",
                "收盘价跌破了吗？还是只是盘中晃了一下？",
            ],
            "D": [  # 长线配置
                "这只票在你的曼城首发阵容里吗？还是你想炒一把？",
                "它是不是'一提到就不需要解释'的稀缺资产？",
                "你的钱是闲钱吧？能放半年不涨不动心？",
                "你觉得这票现在在周期的什么位置？起步期、加速期、还是人人都知道能赚钱了？",
            ],
        }
        return questions.get(route, [])

    @classmethod
    def check_position_alert(cls, position_pct_str: str) -> tuple[bool, str]:
        """Check if position size triggers alert.

        Returns:
            (triggered, message)
        """
        try:
            # Parse percentage string like "30%", "满仓", "梭哈"
            pct_str = position_pct_str.strip()

            if any(kw in pct_str for kw in ["满仓", "梭哈", "全仓", "all"]):
                return True, (
                    "单票仓位超过 10% 就是你把命交给运气了。2017 年我管产品的时候，"
                    "单票上限 10%，震荡市 5%，下跌市 2-3%。这不是保守，这是活到下一把桌的门票。"
                )

            # Try to parse numeric percentage
            pct_val = float(pct_str.replace("%", "").strip())
            if pct_val > 10:
                return True, (
                    f"单票仓位 {pct_val}% 已经超过 10% 了。"
                    "这不是保守，这是活到下一把桌的门票。"
                )
        except (ValueError, AttributeError):
            pass

        return False, ""

    @classmethod
    def generate_diagnosis(
        cls,
        route: str,
        answers: dict[int, dict],
        strategy_signals: dict,
    ) -> str:
        """Generate diagnosis conclusion based on route and answers.

        This is a rule-based helper; the actual persona-flavored conclusion
        should come from ResponseGenerator with LLM.
        """
        round1 = answers.get(1, {})
        round2 = answers.get(2, {})

        conclusions = []

        if route == "A":  # 持仓诊断
            cost = round2.get("cost", "")
            pnl = round2.get("pnl", "")
            signal = round2.get("signal", "")
            days = round2.get("days", "")

            if days and int(str(days).replace("天", "")) <= 3:
                conclusions.append("买入后 ≤3 天不涨，少妇战法纪律：次日 9:33/9:37 就该走。")
            if "浮盈转浮亏" in str(pnl):
                conclusions.append("赚钱的票不要做亏，先出来保住本金。")
            if "B1" in str(signal) and "B2" not in str(signal):
                conclusions.append("b1 没玩明白就别捣鼓持仓了，等下一个。")

        elif route == "B":  # 买点确认
            j_value = round2.get("j_value", "")
            brick = round2.get("brick", "")
            market = round2.get("market", "")
            heard = round2.get("heard", "")

            if "绿" in str(brick):
                conclusions.append("绿砖出现绝不抄底，先数满 4 块。你给我记住。")
            try:
                j = float(str(j_value).replace("J", "").strip())
                if j > -10:
                    conclusions.append("B1 的核心是 J ≤ -10，现在这个位置不是倒车接人，是接飞刀。")
            except (ValueError, TypeError):
                pass
            if "-2.3" in str(market) or "负" in str(market):
                conclusions.append("大盘概率不对，七亏三输的时候，宁可错过不做错。")
            if "别人" in str(heard) or "听" in str(heard):
                conclusions.append(
                    "看别人抄底成功自己也要试一试？"
                    "你自己的交易系统里没有这个信号，就别动。"
                )

        elif route == "C":  # 逃命判断
            reason = round2.get("reason", "")
            stop = round2.get("stop", "")
            close_broke = round2.get("close_broke", "")

            if "心里慌" in str(reason) or "慌" in str(reason):
                conclusions.append("看收盘价，不看盘中。盘中是主力折腾你的。")
            if "BBI" in str(stop) and "连续两天" in str(close_broke):
                conclusions.append("两日破位，清仓走人。横盘不动也走。")
            if "无利空" in str(reason) or "暴跌" in str(reason):
                conclusions.append("没利空消息的暴跌不卖。有本事打我止损。")

        elif route == "D":  # 长线配置
            scarcity = round2.get("scarcity", "")
            idle_money = round2.get("idle_money", "")
            cycle_pos = round2.get("cycle_pos", "")

            if "不是" in str(scarcity) or "否" in str(scarcity):
                conclusions.append("长线拿稀缺，短线做交易。你这票没有稀缺性，不适合长拿。")
            if "不是" in str(idle_money) or "否" in str(idle_money) or "急" in str(idle_money):
                conclusions.append("不急用的钱才能做长线。急用的钱去做短线纪律更清楚。")
            if "人人都知道" in str(cycle_pos) or "末期" in str(cycle_pos):
                conclusions.append("人人都知道能赚钱的时候，就是该出货的时候了。逆向。")

        if not conclusions:
            conclusions.append("信息还不够，我再看看。")

        return "\n".join(conclusions)
