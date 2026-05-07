"""Trend indicators from Zettaranc trading system."""
import pandas as pd
from quant.registry import register_indicator


@register_indicator("ZX_DOUBLE_LINE", category="trend")
def calculate_double_line(df: pd.DataFrame) -> dict:
    """Zettaranc double-line system: white line (short-term) + yellow line (medium-term).

    White line (牵牛绳): EMA(EMA(close, 10), 10) - double-smoothed EMA
    Yellow line (大哥线): (MA14 + MA28 + MA57 + MA114) / 4 - BBI-like long-period average

    Returns:
        dict with keys: white_line, yellow_line, golden_cross, dead_cross,
                        white_above_yellow, distance, position
    """
    close = df["close"]

    # White line: double EMA(10)
    white = close.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

    # Yellow line: average of 4 long-period MAs
    ma14 = close.rolling(window=14).mean()
    ma28 = close.rolling(window=28).mean()
    ma57 = close.rolling(window=57).mean()
    ma114 = close.rolling(window=114).mean()
    yellow = (ma14 + ma28 + ma57 + ma114) / 4

    # Cross detection
    white_above = white > yellow
    golden_cross = (~white_above.shift(1).fillna(False)) & white_above
    dead_cross = (white_above.shift(1).fillna(False)) & (~white_above)

    # Distance between lines (乖离)
    distance = (white - yellow) / yellow * 100

    # Position classification
    def classify_position(row):
        w, y, c = row["white"], row["yellow"], row["close"]
        if pd.isna(w) or pd.isna(y):
            return "unknown"
        if w > y and c > y:
            return "strong"  # 白上黄上 + 股价在黄线上
        if w > y and c <= y:
            return "weak_bounce"  # 白上黄上但股价跌破黄线
        if w <= y:
            return "bearish"  # 白下黄下
        return "unknown"

    result_df = pd.DataFrame({"white": white, "yellow": yellow, "close": close})
    position = result_df.apply(classify_position, axis=1)

    return {
        "white_line": white,
        "yellow_line": yellow,
        "golden_cross": golden_cross,
        "dead_cross": dead_cross,
        "white_above_yellow": white_above,
        "distance_pct": distance,
        "position": position,
    }


@register_indicator("ZX_BBI", category="trend")
def calculate_bbi(df: pd.DataFrame) -> pd.Series:
    """BBI (Bull and Bear Index) - Zettaranc version.

    BBI = (MA3 + MA6 + MA12 + MA24) / 4
    Used as the purple line in the young-wife strategy (少妇战法).
    """
    close = df["close"]
    ma3 = close.rolling(window=3).mean()
    ma6 = close.rolling(window=6).mean()
    ma12 = close.rolling(window=12).mean()
    ma24 = close.rolling(window=24).mean()
    return (ma3 + ma6 + ma12 + ma24) / 4
