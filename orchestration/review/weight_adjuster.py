# orchestration/review/weight_adjuster.py
from orchestration.review.models import ReviewResult


class WeightAdjuster:
    """根据历史表现调整指标权重"""

    def __init__(
        self,
        min_weight: float = 0.1,
        max_weight: float = 1.0,
        step: float = 0.1,
        high_threshold: float = 0.7,
        low_threshold: float = 0.5
    ):
        self.min_weight = min_weight
        self.max_weight = max_weight
        self.step = step
        self.high_threshold = high_threshold
        self.low_threshold = low_threshold

    def compute_adjustments(self, result: ReviewResult) -> dict:
        """计算权重调整

        规则：
        - 准确率 > 70%: 权重 +0.1
        - 准确率 50-70%: 权重不变
        - 准确率 < 50%: 权重 -0.1
        """
        adjustments = {}

        for source, stats in result.by_source.items():
            accuracy = stats.get("accuracy", 0.5)
            if accuracy > self.high_threshold:
                adjustments[source] = self.step  # 增加
            elif accuracy < self.low_threshold:
                adjustments[source] = -self.step  # 减少
            else:
                adjustments[source] = 0  # 不变

        return adjustments