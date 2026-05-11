from agent_team.core.models import TeamResult


class InfographicFormatter:
    def format(self, result: TeamResult) -> str:
        lines = ["# PersonaX 团队分析报告", ""]

        for round_result in result.rounds:
            lines.append(f"## 第 {round_result.round_num} 轮分析")
            for thought in round_result.thoughts:
                content = thought.content[:120]
                lines.append(f"- **{thought.agent_name}**: {content}")
                lines.append(f"  - 置信度: {thought.confidence:.0%}")
            lines.append("")

        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append("## 主持人汇总")
            lines.append(f"- **共识**: {summary.consensus}")
            lines.append(f"- **建议**: {summary.recommendation}")
            lines.append("")

        if result.final_scores:
            lines.append("## 用户评分")
            for agent, score in result.final_scores.items():
                lines.append(f"- {agent}: {score} {'⭐' * int(score)}")
            lines.append("")

        return "\n".join(lines)
