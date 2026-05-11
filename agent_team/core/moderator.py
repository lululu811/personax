"""Moderator agent that synthesizes multiple thoughts into a summary."""

from orchestration.response_generator import ResponseGenerator, GenerationContext
from agent_team.core.models import Thought, Synthesis


class Moderator:
    """Moderator synthesizes team thoughts into a structured conclusion.

    Does not do market analysis — only summarizes, contrasts, and reconciles.
    """

    def __init__(self, persona_config=None):
        self.persona_config = persona_config
        self.generator = ResponseGenerator()

    def synthesize(self, thoughts: list[Thought], mode: str) -> Synthesis:
        """Synthesize thoughts into structured conclusion."""
        if self.generator.llm_available and self.persona_config:
            return self._synthesize_llm(thoughts, mode)
        return self._synthesize_template(thoughts)

    def _synthesize_llm(self, thoughts: list[Thought], mode: str) -> Synthesis:
        thoughts_text = "\n\n".join([
            f"【{t.agent_name}】(置信度 {t.confidence:.0%}): {t.content[:200]}"
            for t in thoughts
        ])

        prompt = (
            f"你是一位中立的分析主持人。以下多位分析师对同一问题的观点:\n\n"
            f"{thoughts_text}\n\n"
            f"请用中文总结:\n"
            f"1. 【共识】大家一致认同的部分\n"
            f"2. 【分歧】存在争议的部分，列出各方立场\n"
            f"3. 【建议】综合所有观点后给出的操作建议\n"
            f"4. 【风险提示】需要特别关注的风险点"
        )

        analysis = self.generator.generate(
            query=prompt,
            persona_config=self.persona_config,
            context=GenerationContext(),
        )

        return Synthesis(
            consensus=self._extract_section(analysis, "共识"),
            disagreements=self._extract_disagreements(analysis, thoughts),
            recommendation=self._extract_section(analysis, "建议"),
            confidence=self._compute_avg_confidence(thoughts),
        )

    def _synthesize_template(self, thoughts: list[Thought]) -> Synthesis:
        """Template-based synthesis when LLM is unavailable."""
        actions = {t.action: [] for t in thoughts}
        for t in thoughts:
            actions[t.action].append(t.agent_name)

        consensus_parts = []
        disagreements = []

        # Find majority action
        majority_action = max(actions, key=lambda k: len(actions[k])) if actions else "unknown"

        if len(set(actions.keys())) == 1:
            consensus_parts.append(f"所有分析师一致认为: {majority_action}")
        else:
            consensus_parts.append("分析师之间存在分歧")
            for action, agents in actions.items():
                if action != majority_action:
                    disagreements.append({
                        "agents": agents,
                        "stance": action,
                    })

        avg_conf = sum(t.confidence for t in thoughts) / len(thoughts) if thoughts else 0.0

        return Synthesis(
            consensus="; ".join(consensus_parts),
            disagreements=disagreements,
            recommendation=f"多数观点倾向于: {majority_action} (参与分析师: {', '.join(actions.get(majority_action, []))})",
            confidence=avg_conf,
        )

    def _extract_section(self, text: str, section_name: str) -> str:
        """Extract a section from LLM output."""
        import re
        pattern = rf"【?{section_name}】?[:：]?(.*?)(?=【|$)"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else f"未提取到{section_name}"

    def _extract_disagreements(self, text: str, thoughts: list[Thought]) -> list[dict]:
        """Extract disagreements from LLM output."""
        import re
        # Simple extraction: look for bullet points under 分歧 section
        section = self._extract_section(text, "分歧")
        lines = [l.strip() for l in section.split("\n") if l.strip().startswith(("-", "•", "1.", "2.", "3."))]
        return [{"agents": [], "stance": line.lstrip("- •123456789.")} for line in lines[:3]]

    def _compute_avg_confidence(self, thoughts: list[Thought]) -> float:
        if not thoughts:
            return 0.0
        return sum(t.confidence for t in thoughts) / len(thoughts)
