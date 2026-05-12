# orchestration/review/evaluator.py
from datetime import datetime, timedelta
from orchestration.review.models import SignalRecord, SignalAction


class Evaluator:
    """用技术指标验证信号对错"""

    def __init__(self, holding_days: int = 5):
        self.holding_days = holding_days

    def evaluate(self, record: SignalRecord, current_price: float) -> str:
        """评估信号对错

        逻辑：
        - BUY 信号：如果后续价格 > 信号价格，正确
        - SELL 信号：如果后续价格 < 信号价格，正确
        """
        if record.action == SignalAction.BUY:
            return "correct" if current_price > record.price else "incorrect"
        elif record.action == SignalAction.SELL:
            return "correct" if current_price < record.price else "incorrect"
        else:
            return "pending"

    def get_outcome_price(self, asset: str, signal_timestamp: datetime) -> float:
        """获取信号产生后 N 天的价格

        TODO: 接入 Tushare 获取历史价格
        目前返回模拟价格
        """
        return 0.0