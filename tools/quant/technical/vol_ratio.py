"""量比指标 - 攻击日/震荡日/出货日判断

Z 哥量价关系核心工具。

量比 = 当日成交量 / 过去 N 日平均成交量

信号：
  attack_day: 量比 > 20 且价格上涨（攻击日，立即买）
  distribution_day: 量比 > 20 且价格暴跌（出货日，观望）
  shakeout_day: 量比 10-20 且量价齐升（单向拉升）
  normal_day: 量比 < 10（震荡日，慢买/观望）
  weak_day: 量比 10-20 且低开（弱势）

铁律：
- 量比 > 20 + 涨 → 攻击日，立即买
- 量比 > 20 + 暴跌 → 出货日，别接飞刀
- 量比 < 10 → 慢买或观望
- 量比 10-20 + 量价齐升 → 可买
"""

import pandas as pd

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    SignalType,
    TechnicalTool,
    register_tool,
)


class VolRatioTool:
    name = "vol_ratio"
    description = "量比战法：量比 >20 攻击日，<10 震荡日，判断买卖时机"

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            close = data["close"]
            vol = data["vol"] if "vol" in data.columns else data["volume"]
            open_ = data["open"]
            pre_close = data["pre_close"] if "pre_close" in data.columns else close.shift(1)
        else:
            close = data.close
            vol = data.vol
            open_ = data.open
            pre_close = close.shift(1)

        # 量比 = 当日成交量 / 过去 20 日平均成交量
        vol_avg_20 = vol.rolling(window=20).mean()
        vol_ratio = vol / vol_avg_20

        # 价格变化
        price_change_pct = close.pct_change() * 100
        is_up = close > pre_close
        is_big_drop = price_change_pct < -3  # 暴跌阈值

        # 低开判断
        is_gap_down = open_ < pre_close * 0.98  # 低开 2% 以上

        # 量价齐升
        vol_up = vol > vol.shift(1)
        price_up = close > close.shift(1)
        vol_price_up = vol_up & price_up

        # 信号分类
        attack_day = (vol_ratio > 20) & is_up & ~is_big_drop
        distribution_day = (vol_ratio > 20) & is_big_drop
        shakeout_day = (vol_ratio.between(10, 20)) & vol_price_up
        normal_day = vol_ratio < 10
        weak_day = (vol_ratio.between(10, 20)) & is_gap_down

        return ToolResult(
            tool_name=self.name,
            data={
                "vol_ratio": vol_ratio,
                "vol_avg_20": vol_avg_20,
                "price_change_pct": price_change_pct,
            },
            signals={
                "attack_day": bool(attack_day.iloc[-1]),
                "distribution_day": bool(distribution_day.iloc[-1]),
                "shakeout_day": bool(shakeout_day.iloc[-1]),
                "normal_day": bool(normal_day.iloc[-1]),
                "weak_day": bool(weak_day.iloc[-1]),
                "should_buy": bool((attack_day | shakeout_day).iloc[-1]),
                "should_wait": bool((distribution_day | weak_day).iloc[-1]),
            },
            metadata={
                "params": {
                    "vol_avg_window": 20,
                    "attack_threshold": 20,
                    "distribution_drop": -3,
                    "gap_down_threshold": -2,
                },
                "description": {
                    "attack_day": "量比>20 且涨（攻击日，立即买）",
                    "distribution_day": "量比>20 且暴跌（出货日，观望）",
                    "shakeout_day": "量比 10-20 量价齐升（可买）",
                    "normal_day": "量比<10（震荡日，慢买/观望）",
                    "weak_day": "量比 10-20 低开（弱势）",
                },
            },
        )


# 注册
vol_ratio = VolRatioTool()
register_tool(vol_ratio)
