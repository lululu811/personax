# orchestration/review/review_service.py
from datetime import datetime, date, timedelta
from orchestration.review.models import SignalEvent, ReviewResult, SignalRecord
from orchestration.review.signal_history import SignalHistory
from orchestration.review.evaluator import Evaluator
from orchestration.review.weight_adjuster import WeightAdjuster
from orchestration.review.event_bus import subscribe


class ReviewService:
    """信号回顾服务"""

    def __init__(
        self,
        db_path: str = "~/.personax/review.db",
        holding_days: int = 5
    ):
        self.signal_history = SignalHistory(db_path=db_path)
        self.evaluator = Evaluator(holding_days=holding_days)
        self.weight_adjuster = WeightAdjuster()
        self.start_listening()

    def start_listening(self):
        """开始监听事件"""
        subscribe("signal", self.on_signal)

    def on_signal(self, event: SignalEvent):
        """接收信号事件，存储到数据库"""
        self.signal_history.add(event)

    def review_weekly(self) -> ReviewResult:
        """每周回顾"""
        today = date.today()
        start = today - timedelta(days=7)
        return self._review(start, today, "weekly")

    def review_monthly(self) -> ReviewResult:
        """每月回顾"""
        today = date.today()
        start = today - timedelta(days=30)
        return self._review(start, today, "monthly")

    def _review(self, start: date, end: date, period: str) -> ReviewResult:
        """执行回顾"""
        records = self.signal_history.get_by_period(start, end)

        total = len(records)
        correct = 0
        incorrect = 0
        pending = 0
        by_source = {}

        for record in records:
            outcome_price = self.evaluator.get_outcome_price(
                record.asset, record.timestamp
            )
            outcome = None
            if outcome_price > 0:
                outcome = self.evaluator.evaluate(record, outcome_price)
                self.signal_history.mark_evaluated(record.id, outcome, outcome_price)

                if outcome == "correct":
                    correct += 1
                elif outcome == "incorrect":
                    incorrect += 1
            else:
                pending += 1

            if record.source not in by_source:
                by_source[record.source] = {"correct": 0, "total": 0, "accuracy": 0}
            by_source[record.source]["total"] += 1
            if outcome == "correct":
                by_source[record.source]["correct"] += 1

        evaluated = total - pending
        accuracy = correct / evaluated if evaluated > 0 else 0.0

        for source in by_source:
            stats = by_source[source]
            stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0

        result = ReviewResult(
            period=period,
            start_date=start,
            end_date=end,
            total_signals=total,
            correct=correct,
            incorrect=incorrect,
            pending=pending,
            accuracy=accuracy,
            by_source=by_source,
            weight_adjustments={},
            report=self._generate_report(period, start, end, total, correct, incorrect, pending, accuracy, by_source)
        )
        result.weight_adjustments = self.weight_adjuster.compute_adjustments(result)

        return result

    def _generate_report(self, period, start, end, total, correct, incorrect, pending, accuracy, by_source) -> str:
        lines = [
            f"## {period.upper()} Review Report",
            f"Period: {start} to {end}",
            f"",
            f"Total Signals: {total}",
            f"Correct: {correct} ({accuracy*100:.1f}%)",
            f"Incorrect: {incorrect}",
            f"Pending: {pending}",
            f"",
            f"### By Source",
        ]
        for source, stats in by_source.items():
            lines.append(f"- {source}: {stats['correct']}/{stats['total']} ({stats['accuracy']*100:.1f}%)")
        return "\n".join(lines)