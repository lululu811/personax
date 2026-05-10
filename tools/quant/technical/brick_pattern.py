"""砖形图指标 - 4 天情绪循环

Z 哥情绪周期判断工具。

核心逻辑：
- 红砖：收盘价 > 开盘价（阳线），且收盘价 > 前一日收盘价
- 绿砖：收盘价 < 开盘价（阴线），或收盘价 < 前一日收盘价
- 4 块砖为一个情绪循环周期

信号：
  red_brick: 今日为红砖
  green_brick: 今日为绿砖
  four_red: 连续 4 块红砖（情绪高潮，至少减仓一半）
  brick_count: 当前连续砖数（1-4）
  brick_pattern: 当前情绪周期描述

铁律：
- 四块红砖走完，至少减仓一半
- 绿砖出现，绝不抄底，先数满 4 块
- 绿砖后重新计数
"""

import pandas as pd

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    SignalType,
    TechnicalTool,
    register_tool,
)


class BrickPatternTool:
    name = "brick_pattern"
    description = "砖形图：4 天情绪循环（红砖/绿砖判断情绪周期）"

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            close = data["close"]
            open_ = data["open"]
        else:
            close = data.close
            open_ = data.open

        n = len(close)
        brick_types = []  # 'red' or 'green'
        brick_counts = []  # 1-4
        patterns = []

        consecutive = 0
        last_type = None

        for i in range(n):
            is_red = (close.iloc[i] > open_.iloc[i]) and (i == 0 or close.iloc[i] > close.iloc[i - 1])
            brick_type = "red" if is_red else "green"

            # 连续计数
            if brick_type == last_type:
                consecutive += 1
            else:
                consecutive = 1
                last_type = brick_type

            # 限制在 4 以内
            count = min(consecutive, 4)

            # 情绪周期描述
            if brick_type == "green":
                pattern = "green"
                consecutive = 0  # 绿砖重置计数
            elif count == 1:
                pattern = "red_1"
            elif count == 2:
                pattern = "red_2"
            elif count == 3:
                pattern = "red_3"
            elif count >= 4:
                pattern = "red_4"

            brick_types.append(brick_type)
            brick_counts.append(count)
            patterns.append(pattern)

        brick_series = pd.Series(brick_types, index=close.index)
        count_series = pd.Series(brick_counts, index=close.index)
        pattern_series = pd.Series(patterns, index=close.index)

        # 信号
        is_green = brick_series.iloc[-1] == "green"
        is_red = brick_series.iloc[-1] == "red"
        is_four_red = count_series.iloc[-1] >= 4

        return ToolResult(
            tool_name=self.name,
            data={
                "brick_type": brick_series,
                "brick_count": count_series,
                "pattern": pattern_series,
            },
            signals={
                "red_brick": is_red,
                "green_brick": is_green,
                "four_red": is_four_red,
                "should_halve": is_four_red,  # 四块红砖，减半
                "no_bottom_fishing": is_green,  # 绿砖不抄底
            },
            metadata={
                "params": {
                    "cycle": "4 天情绪循环",
                    "red_rule": "收盘 > 开盘 且 收盘 > 前一日收盘",
                    "green_rule": "收盘 < 开盘 或 收盘 < 前一日收盘",
                },
                "description": {
                    "four_red": "连续 4 块红砖（情绪高潮，减仓一半）",
                    "green_brick": "绿砖出现（绝不抄底，重新计数）",
                    "should_halve": "应减仓信号",
                    "no_bottom_fishing": "禁止抄底信号",
                },
            },
        )


# 注册
brick_pattern = BrickPatternTool()
register_tool(brick_pattern)
