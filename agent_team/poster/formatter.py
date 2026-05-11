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


class ImageCardsFormatter:
    def format(self, result: TeamResult) -> str:
        lines = ["# 封面", ""]

        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append(f"## {summary.consensus}")
            lines.append(f"{summary.recommendation}")
            lines.append("")

        for round_result in result.rounds:
            for thought in round_result.thoughts:
                lines.append(f"# {thought.agent_name}")
                lines.append(f"{thought.content[:100]}")
                if thought.key_points:
                    for kp in thought.key_points[:3]:
                        kp_text = kp if isinstance(kp, str) else str(kp)
                        lines.append(f"- {kp_text}")
                lines.append(f"置信度: {thought.confidence:.0%}")
                if result.final_scores and thought.agent_name in result.final_scores:
                    score = result.final_scores[thought.agent_name]
                    lines.append(f"评分: {'⭐' * int(score)}")
                lines.append("")

        lines.append("# 总结")
        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append(f"共识: {summary.consensus}")
            lines.append(f"建议: {summary.recommendation}")

        return "\n".join(lines)
