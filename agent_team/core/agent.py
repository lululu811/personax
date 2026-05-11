"""Agent wrapper around persona for team collaboration."""

import re

from orchestration.response_generator import ResponseGenerator, GenerationContext
from agent_team.core.models import Thought, AgentContext


class Agent:
    """An agent that participates in team brainstorming.

    Wraps a persona config and uses ResponseGenerator for LLM calls.
    Does NOT reimplement LLM logic — delegates to existing infrastructure.
    """

    def __init__(self, name: str, persona_config):
        self.name = name
        self.persona_config = persona_config
        self.generator = ResponseGenerator()

    async def think(self, query: str, context: AgentContext) -> Thought:
        """Independent thinking — returns a structured Thought."""
        gen_context = GenerationContext(
            knowledge_snippets=context.knowledge_snippets,
            tool_results=context.tool_results,
            strategy_results=context.strategy_results,
            stock_code=context.stock_code,
            web_search_results=context.web_search_results,
        )

        analysis = self.generator.generate(
            query=query,
            persona_config=self.persona_config,
            context=gen_context,
        )

        return Thought(
            agent_name=self.name,
            content=analysis,
            confidence=self._extract_confidence(analysis),
            key_points=self._extract_key_points(analysis),
            action=self._extract_action(analysis),
        )

    async def react(self, query: str, others_thoughts: list[Thought]) -> Thought:
        """React to others' thoughts — for debate mode."""
        others_summary = "\n\n".join([
            f"【{t.agent_name}】: {t.key_points or t.content[:100]}"
            for t in others_thoughts
        ])

        debate_prompt = (
            f"原问题: {query}\n\n"
            f"其他分析师的观点:\n{others_summary}\n\n"
            f"请针对以上观点，给出你的反驳或补充。"
            f"如果有错误，直接指出；如果有遗漏，补充说明。"
        )

        analysis = self.generator.generate(
            query=debate_prompt,
            persona_config=self.persona_config,
            context=GenerationContext(),
        )

        return Thought(
            agent_name=self.name,
            content=analysis,
            confidence=self._extract_confidence(analysis),
            key_points=self._extract_key_points(analysis),
            action=self._extract_action(analysis),
            is_rebuttal=True,
        )

    def _extract_confidence(self, text: str) -> float:
        """Extract confidence from text (simple heuristic)."""
        if not text:
            return 0.5
        # Look for percentage patterns
        matches = re.findall(r'(\d+)%', text)
        if matches:
            return min(max(int(matches[-1]) / 100, 0.0), 1.0)
        # Look for confidence keywords
        high = any(w in text for w in ["确定", "肯定", "明确", "毫无疑问"])
        low = any(w in text for w in ["可能", "不确定", "或许", "看看"])
        if high and not low:
            return 0.8
        if low and not high:
            return 0.4
        return 0.6

    def _extract_key_points(self, text: str) -> list[str]:
        """Extract key points from text (simple sentence split)."""
        if not text:
            return []
        sentences = [s.strip() for s in text.replace("。", ".").replace("\n", ".").split(".") if s.strip()]
        return sentences[:3]

    def _extract_action(self, text: str) -> str:
        """Extract action signal from text."""
        if not text:
            return "unknown"
        text_lower = text.lower()
        if any(w in text_lower for w in ["买入", "建仓", "看多", "机会", "买"]):
            return "buy"
        if any(w in text_lower for w in ["卖出", "清仓", "看空", "逃命", "卖"]):
            return "sell"
        if any(w in text_lower for w in ["持有", "观望", "等待", "hold"]):
            return "hold"
        if any(w in text_lower for w in ["风险", "警告", "注意", "跌破"]):
            return "warning"
        return "unknown"
