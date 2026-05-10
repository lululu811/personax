"""双线战法指标 - 白线 + 黄线

Z 哥核心趋势判断工具。

白线 = EMA(EMA(C, 10), 10)  ← 短期趋势（牛绳）
黄线 = (MA14 + MA28 + MA57 + MA114) / 4  ← 多空线/大哥线

信号：
  white_above_yellow: 白线在黄线之上（多头，可操作）
  white_below_yellow: 白线在黄线之下（空头，管住手）
  golden_cross: 白线上穿黄线（转多信号）
  dead_cross: 白线下穿黄线（转空信号，最后离场）
  white_bowl: 碗口形态（白线从下方向上穿越黄线后回踩不破）
"""

import pandas as pd

from tools.quant.technical.interface import (
    OHLCV,
    ToolResult,
    SignalType,
    TechnicalTool,
    register_tool,
)


def compute_white_line(close: pd.Series) -> pd.Series:
    """白线 = EMA(EMA(C, 10), 10)"""
    ema10 = close.ewm(span=10, adjust=False).mean()
    white = ema10.ewm(span=10, adjust=False).mean()
    return white


def compute_yellow_line(close: pd.Series) -> pd.Series:
    """黄线 = (MA14 + MA28 + MA57 + MA114) / 4"""
    ma14 = close.rolling(window=14).mean()
    ma28 = close.rolling(window=28).mean()
    ma57 = close.rolling(window=57).mean()
    ma114 = close.rolling(window=114).mean()
    yellow = (ma14 + ma28 + ma57 + ma114) / 4
    return yellow


class DoubleLineTool:
    name = "double_line"
    description = "双线战法：白线 EMA(EMA(C,10),10) + 黄线 (MA14+28+57+114)/4"

    def compute(self, data: OHLCV | pd.DataFrame) -> ToolResult:
        if isinstance(data, pd.DataFrame):
            close = data["close"]
        else:
            close = data.close

        white = compute_white_line(close)
        yellow = compute_yellow_line(close)

        # 穿越信号
        prev_white = white.shift(1)
        prev_yellow = yellow.shift(1)

        golden_cross = (prev_white < prev_yellow) & (white > yellow)
        dead_cross = (prev_white > prev_yellow) & (white < yellow)

        # 碗口形态：白线在黄线之上，且近 3 日白线曾回踩接近黄线（差值 < 1%）
        gap_pct = ((white - yellow) / yellow * 100).abs()
        white_bowl = (white > yellow) & (gap_pct.rolling(3).min() < 1.0)

        return ToolResult(
            tool_name=self.name,
            data={
                "white": white,
                "yellow": yellow,
            },
            signals={
                "white_above_yellow": bool((white > yellow).iloc[-1]),
                "white_below_yellow": bool((white < yellow).iloc[-1]),
                "golden_cross": bool(golden_cross.iloc[-1]),
                "dead_cross": bool(dead_cross.iloc[-1]),
                "white_bowl": bool(white_bowl.iloc[-1]),
            },
            metadata={
                "params": {
                    "white": "EMA(EMA(C,10),10)",
                    "yellow": "(MA14+MA28+MA57+MA114)/4",
                },
                "description": {
                    "white_above_yellow": "白线在黄线上（多头）",
                    "white_below_yellow": "白线在黄线下（空头）",
                    "golden_cross": "白线上穿黄线（转多）",
                    "dead_cross": "白线下穿黄线（最后离场）",
                    "white_bowl": "碗口形态（回踩确认）",
                },
            },
        )


# 注册
double_line = DoubleLineTool()
register_tool(double_line)
