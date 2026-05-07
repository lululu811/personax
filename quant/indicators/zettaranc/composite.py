"""Composite indicators combining multiple Zettaranc signals."""

import pandas as pd
from quant.registry import register_indicator


@register_indicator("ZX_B2_BREAK", category="composite")
def detect_b2_break(df: pd.DataFrame) -> pd.Series:
    """B2 breakthrough signal - confirmation after B1.

    Five screening conditions:
    1. Must follow B1 (J < 13 within last 5 days)
    2. Gain >= 4%
    3. Volume > previous day * 1.2
    4. KDJ J < 55
    5. No long upper shadow (upper / body < 0.5)
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["vol"]

    # KDJ J value
    lowest_low = low.rolling(window=9).min()
    highest_high = high.rolling(window=9).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(0)
    k = rsv.rolling(window=3).mean()
    d = k.rolling(window=3).mean()
    j = 3 * k - 2 * d

    # Condition 1: B1 within last 5 days (J < 13)
    b1_signal = j < 13
    has_b1_recently = b1_signal.rolling(window=5).max().fillna(0).astype(bool)

    # Condition 2: Gain >= 4%
    gain_pct = (close - close.shift(1)) / close.shift(1) * 100
    big_gain = gain_pct >= 4.0

    # Condition 3: Volume surge > 20%
    volume_surge = volume > volume.shift(1) * 1.2

    # Condition 4: J < 55
    j_below_55 = j < 55

    # Condition 5: No long upper shadow
    body = abs(close - open_)
    upper_shadow = high - close.where(close >= open_, open_)
    no_long_shadow = (upper_shadow / body) < 0.5
    no_long_shadow = no_long_shadow | (body == 0)  # Handle doji

    return has_b1_recently & big_gain & volume_surge & j_below_55 & no_long_shadow


@register_indicator("ZX_FIVE_SCORE", category="composite")
def calculate_five_score(df: pd.DataFrame) -> pd.Series:
    """Five-point scoring system for position management.

    Daily scoring on 5 dimensions:
    1. Close rising (1pt if close > prev_close)
    2. Above BBI (1pt if close > BBI)
    3. No huge bearish candle (1pt if not巨量阴线)
    4. Trend up (1pt if N-structure intact)
    5. KDJ not dead cross (1pt if J > D)

    Score interpretation:
    5 = hold firmly / 4 = hold / 3 = halve / <=2 = exit
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["vol"]

    score = pd.Series(0, index=df.index)

    # 1. Close rising
    score += (close > close.shift(1)).astype(int)

    # 2. Above BBI
    ma3 = close.rolling(window=3).mean()
    ma6 = close.rolling(window=6).mean()
    ma12 = close.rolling(window=12).mean()
    ma24 = close.rolling(window=24).mean()
    bbi = (ma3 + ma6 + ma12 + ma24) / 4
    score += (close > bbi).astype(int)

    # 3. No huge bearish candle
    body = close - open_
    is_bearish = body < 0
    avg_volume = volume.rolling(window=20).mean()
    is_huge_volume = volume > avg_volume * 2.5
    huge_bearish = is_bearish & is_huge_volume
    score += (~huge_bearish).astype(int)

    # 4. Trend up (higher lows in recent 10 days)
    higher_lows = low.rolling(window=10).apply(lambda x: 1 if x.is_monotonic_increasing else 0, raw=False)
    higher_lows = higher_lows.fillna(0).astype(bool)
    score += higher_lows.astype(int)

    # 5. KDJ not dead cross (J > D)
    lowest_low = low.rolling(window=9).min()
    highest_high = high.rolling(window=9).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(0)
    k = rsv.rolling(window=3).mean()
    d = k.rolling(window=3).mean()
    j = 3 * k - 2 * d
    score += (j > d).astype(int)

    return score


@register_indicator("ZX_SB1", category="composite")
def detect_sb1_fake_fall(df: pd.DataFrame) -> pd.Series:
    """SB1 fake-fall strategy signal.

    Three conditions for fake-fall identification:
    1. Breaks previous low (诱空)
    2. Next day strong reversal (收复前低, 阳包阴)
    3. Reversal with volume surge (放量确认)

    Returns signal on the reversal day.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["vol"]

    # 1. Breaks previous low (today's low < yesterday's low)
    breaks_low = low < low.shift(1)

    # 2. Next day reversal
    next_day_bullish = close.shift(-1) > open_.shift(-1)
    next_day_covers = close.shift(-1) > high  # Reclaims today's high

    # 3. Next day volume surge
    avg_volume = volume.rolling(window=20).mean()
    next_day_volume = volume.shift(-1) > avg_volume * 1.5

    # Signal appears on the day BEFORE the reversal (the fall day)
    signal = breaks_low & next_day_bullish.shift(-1).fillna(False) & next_day_covers.shift(-1).fillna(False) & next_day_volume.shift(-1).fillna(False)

    return signal


@register_indicator("ZX_S1", category="composite")
def detect_s1_warning(df: pd.DataFrame) -> pd.Series:
    """S1 top warning signal.

    High volume at relative high (regardless of bullish/bearish candle).
    Volume significantly higher than recent average.
    """
    close = df["close"]
    volume = df["vol"]

    # Relative high (within top 20% of last 20 days)
    recent_high = close.rolling(window=20).max()
    at_relative_high = close >= recent_high * 0.85

    # Volume surge (> 2.5x average)
    avg_volume = volume.rolling(window=20).mean()
    volume_surge = volume > avg_volume * 2.5

    return at_relative_high & volume_surge


@register_indicator("ZX_HALF_RELEASE", category="composite")
def detect_half_release(df: pd.DataFrame, distance_threshold: float = 8.0) -> pd.Series:
    """Half-position release signal when white line deviates too far from yellow.

    When distance between white and yellow lines exceeds threshold,
    it indicates overbought condition - reduce position by half.

    Args:
        distance_threshold: Percentage deviation threshold (default 8%)
    """
    close = df["close"]

    # White line
    white = close.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

    # Yellow line
    ma14 = close.rolling(window=14).mean()
    ma28 = close.rolling(window=28).mean()
    ma57 = close.rolling(window=57).mean()
    ma114 = close.rolling(window=114).mean()
    yellow = (ma14 + ma28 + ma57 + ma114) / 4

    # Distance
    distance = (white - yellow) / yellow * 100

    return distance > distance_threshold


@register_indicator("ZX_ULTIMATE_B1", category="composite")
def ultimate_b1_screener(df: pd.DataFrame) -> pd.Series:
    """Ultimate B1 stock screener combining multiple filters.

    Conditions:
    1. White above yellow (白上黄上)
    2. B1 signal (J < 13)
    3. Price above yellow line
    4. Not in third wave (simple check: not after two recent highs)
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # White line
    white = close.ewm(span=10, adjust=False).mean().ewm(span=10, adjust=False).mean()

    # Yellow line
    ma14 = close.rolling(window=14).mean()
    ma28 = close.rolling(window=28).mean()
    ma57 = close.rolling(window=57).mean()
    ma114 = close.rolling(window=114).mean()
    yellow = (ma14 + ma28 + ma57 + ma114) / 4

    # Condition 1: White above yellow
    white_above_yellow = white > yellow

    # Condition 2: B1 signal (J < 13)
    lowest_low = low.rolling(window=9).min()
    highest_high = high.rolling(window=9).max()
    rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
    rsv = rsv.fillna(0)
    k = rsv.rolling(window=3).mean()
    d = k.rolling(window=3).mean()
    j = 3 * k - 2 * d
    b1_signal = j < 13

    # Condition 3: Price above yellow
    price_above_yellow = close > yellow

    # Condition 4: Not third wave (simplified: no two recent peaks)
    # Count recent local maxima in last 30 days
    is_local_max = (close > close.shift(1)) & (close > close.shift(2)) & (close > close.shift(-1)) & (close > close.shift(-2))
    recent_peaks = is_local_max.rolling(window=30).sum().fillna(0)
    not_third_wave = recent_peaks < 2

    return white_above_yellow & b1_signal & price_above_yellow & not_third_wave
