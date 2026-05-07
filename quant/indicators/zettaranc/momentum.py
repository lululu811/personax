"""Momentum indicators from Zettaranc trading system."""
import pandas as pd
from quant.registry import register_indicator


@register_indicator("ZX_KDJ", category="momentum")
def calculate_kdj(df: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> dict:
    """KDJ indicator with Zettaranc B1 signal detection.

    Standard KDJ formula:
        RSV = (CLOSE - LLV(LOW, N)) / (HHV(HIGH, N) - LLV(LOW, N)) * 100
        K = SMA(RSV, M1, 1)
        D = SMA(K, M2, 1)
        J = 3*K - 2*D

    B1 signal: J < 13 (general) or J < -10 (conservative/young-wife strategy)
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    lowest_low = low.rolling(window=n).min()
    highest_high = high.rolling(window=n).max()

    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(0)

    # SMA with weight 1 = simple moving average of the last M1 values
    k = rsv.rolling(window=m1).mean()
    d = k.rolling(window=m2).mean()
    j = 3 * k - 2 * d

    # B1 signals
    b1_general = j < 13
    b1_conservative = j < -10

    # Golden/Dead cross
    k_above_d = k > d
    kdj_golden = (~k_above_d.shift(1).fillna(False)) & k_above_d
    kdj_dead = (k_above_d.shift(1).fillna(False)) & (~k_above_d)

    return {
        "K": k,
        "D": d,
        "J": j,
        "B1_signal": b1_general,
        "B1_strict": b1_conservative,
        "golden_cross": kdj_golden,
        "dead_cross": kdj_dead,
    }


@register_indicator("ZX_SINGLE_NEEDLE", category="momentum")
def calculate_single_needle(df: pd.DataFrame, n1: int = 5, n2: int = 60) -> dict:
    """Single-needle stochastic indicator (单针代码).

    Four stochastic lines representing different timeframes:
        Short-term (white):  100*(C-LLV(L,N1))/(HHV(H,N1)-LLV(L,N1))
        Medium-term (yellow): 100*(C-LLV(L,10))/(HHV(H,10)-LLV(L,10))
        Mid-long-term (purple): 100*(C-LLV(L,20))/(HHV(H,20)-LLV(L,20))
        Long-term (red): 100*(C-LLV(L,N2))/(HHV(H,N2)-LLV(L,N2))

    Buy signals:
        Four-line-zero: all four <= 6
        White-below-20: short <= 20 and long >= 60
        White-cross-red: CROSS(short, long) and long < 20
        White-cross-yellow: CROSS(short, medium) and medium < 30
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    def stochastic(c, h, l, n):
        ll = l.rolling(window=n).min()
        hh = h.rolling(window=n).max()
        return (c - ll) / (hh - ll) * 100

    short = stochastic(close, high, low, n1)      # white line
    medium = stochastic(close, high, low, 10)     # yellow line
    mid_long = stochastic(close, high, low, 20)   # purple line
    long_term = stochastic(close, high, low, n2)  # red line

    # Buy signals
    four_zero = (short <= 6) & (medium <= 6) & (mid_long <= 6) & (long_term <= 6)
    white_below_20 = (short <= 20) & (long_term >= 60)

    # Cross detection
    short_above_long = short > long_term
    white_cross_red = (~short_above_long.shift(1).fillna(False)) & short_above_long & (long_term < 20)

    short_above_medium = short > medium
    white_cross_yellow = (~short_above_medium.shift(1).fillna(False)) & short_above_medium & (medium < 30)

    return {
        "short": short,
        "medium": medium,
        "mid_long": mid_long,
        "long": long_term,
        "four_line_zero": four_zero,
        "white_below_20": white_below_20,
        "white_cross_red": white_cross_red,
        "white_cross_yellow": white_cross_yellow,
    }


@register_indicator("ZX_RSI_3", category="momentum")
def calculate_rsi_3(df: pd.DataFrame, period: int = 3) -> dict:
    """RSI with period 3 (Zettaranc specific settings).

    From Z哥's knowledge base:
    "RSI，参数都设置成3以后，那20和80为边界，
     跌下20以下是近期低点，也是买点，涨到80以上就是近期的高点。"

    Standard RSI formula:
        RS = SMA(UP, N) / SMA(DOWN, N)
        RSI = 100 - 100 / (1 + RS)

    Zettaranc-specific interpretation:
    - RSI < 20: recent low, potential buy point (B1 zone)
    - RSI > 80: recent high, potential sell/take-profit zone
    - Period = 3 for maximum sensitivity (short-term swings)

    Args:
        df: DataFrame with close column
        period: RSI period (default 3 per Z哥's setting)

    Returns:
        dict with RSI values and signals
    """
    close = df["close"]

    # Price changes
    delta = close.diff()

    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)

    # Average gain and loss using SMA
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()

    # RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # Zettaranc signals
    oversold = rsi < 20      # Below 20 = recent low, buy zone
    overbought = rsi > 80    # Above 80 = recent high, sell zone

    return {
        "rsi": rsi,
        "oversold": oversold,
        "overbought": overbought,
    }
