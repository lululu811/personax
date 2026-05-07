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


@register_indicator("ZX_SUPER_B1", category="composite")
def detect_super_b1(df: pd.DataFrame) -> pd.Series:
    """Super B1 signal - advanced B1 after extreme shakeout.

    Conditions (from Z哥's knowledge base):
    1. N-shaped uptrend structure (higher lows intact)
    2. Breathing structure: price up with volume (exhale) → pullback with shrinking volume (inhale)
    3. Sudden heavy volume bearish candle (breaks support, shakes out weak hands)
    4. Continued shrinking volume stabilization (volume dries up after shakeout)
    5. KDJ J value goes deeply negative (J < -10 is the key signal)

    Key principle: "放量可以作假，缩量骗不了人" - volume shrinkage cannot be faked.
    Super B1 is a high-risk, high-reward play. Set stop-loss at the low of the
    heavy volume bearish candle. Only bet once per signal.
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

    # Condition 1: N-shaped structure - recent higher lows
    # At least one higher low in the last 20 days
    recent_lows = low.rolling(window=20).min()
    prev_recent_lows = recent_lows.shift(10)
    higher_lows = recent_lows > prev_recent_lows

    # Condition 2: Breathing structure detected recently
    # Exhale (放量上涨) → Inhale (缩量回调)
    vol_avg = volume.rolling(window=10).mean()
    exhale = (close > close.shift(1)) & (volume > vol_avg)
    inhale = (close < close.shift(1)) & (volume < vol_avg * 0.7)
    has_breathing = (exhale.rolling(window=10).sum() >= 1) & (inhale.rolling(window=10).sum() >= 1)

    # Condition 3: Sudden heavy volume bearish candle (shakeout)
    # Volume >= 2x average AND bearish candle with significant decline
    avg_vol_20 = volume.rolling(window=20).mean()
    heavy_volume = volume >= avg_vol_20 * 2.0
    bearish = close < open_
    significant_decline = (open_ - close) / open_ * 100 >= 2.0  # At least 2% decline
    shakeout = heavy_volume & bearish & significant_decline
    has_shakeout_recently = shakeout.rolling(window=5).max().fillna(0).astype(bool)

    # Condition 4: Volume shrinks after shakeout (current volume < 0.8x avg)
    volume_shrinks = volume < avg_vol_20 * 0.8

    # Condition 5: J deeply negative (J < -10 for conservative, J < 0 for general)
    j_deep_negative = j < -10

    # Combined: need breathing structure + recent shakeout + volume shrinks + J negative
    return has_breathing & has_shakeout_recently & volume_shrinks & j_deep_negative & higher_lows


@register_indicator("ZX_N_STRUCTURE", category="composite")
def detect_n_structure(df: pd.DataFrame, lookback: int = 30) -> pd.Series:
    """Detect N-shaped uptrend structure.

    N-structure = up wave → pullback (doesn't break previous low) → up again

    Conditions:
    1. First wave up: price rises from a local low
    2. Pullback: price declines but doesn't break the starting low of first wave
    3. Second wave up: price rises again from the pullback low

    Key principle from Z哥: N-shaped uptrend + breathing structure = best setup.
    "缩量是最好的，因为放量可以作假，缩量骗不了人"
    """
    close = df["close"]
    low = df["low"]

    # Find local extrema in the lookback window
    # Local minimum: lower than neighbors
    is_local_min = (low < low.shift(1)) & (low < low.shift(2)) & (low < low.shift(-1)) & (low < low.shift(-2))
    # Local maximum: higher than neighbors
    is_local_max = (close > close.shift(1)) & (close > close.shift(2)) & (close > close.shift(-1)) & (close > close.shift(-2))

    # For each day, check if there's a valid N-structure in the recent lookback
    n_structure = pd.Series(False, index=df.index)

    for i in range(lookback, len(df)):
        window = df.iloc[i-lookback:i+1]
        window_lows = window["low"]
        window_close = window["close"]

        # Find two local minima with a local maximum between them
        min_indices = window_lows[is_local_min.iloc[i-lookback:i+1]].index
        max_indices = window_close[is_local_max.iloc[i-lookback:i+1]].index

        if len(min_indices) >= 2 and len(max_indices) >= 1:
            # Check if we have: low1 < peak > low2 and low2 >= low1 (doesn't break)
            for j_idx in range(len(min_indices) - 1):
                low1_idx = min_indices[j_idx]
                low2_idx = min_indices[j_idx + 1]

                # Find a peak between the two lows
                peaks_between = [p for p in max_indices if p > low1_idx and p < low2_idx]
                if peaks_between:
                    peak_idx = peaks_between[0]
                    low1 = window_lows.loc[low1_idx]
                    low2 = window_lows.loc[low2_idx]
                    peak = window_close.loc[peak_idx]

                    # N-structure: low1 < peak and low2 >= low1 (doesn't break previous low)
                    # Also ensure meaningful rise: peak > low1 * 1.05 (at least 5% rise)
                    if peak > low1 * 1.05 and low2 >= low1 * 0.98:
                        n_structure.iloc[i] = True
                        break

    return n_structure


@register_indicator("ZX_TWIST", category="composite")
def detect_twist(df: pd.DataFrame) -> dict:
    """Detect "扭一扭" (twist) - moving average bullish alignment.

    Traditional term: 多头排列 (bullish alignment of moving averages)
    But Z哥 emphasizes: only LOW-position bullish alignment has value!
    High-position bullish alignment can be a trap.

    Conditions for twist:
    1. Short-term MA > Medium-term MA > Long-term MA
    2. All MAs trending upward (or at least flat)
    3. LOW-position twist: price not far from long-term MA (within 15%)
    4. HIGH-position twist: price far above long-term MA (>30%)

    Returns dict with twist signals and position classification.
    """
    close = df["close"]

    # Calculate MAs (using common periods: 5, 10, 20, 60)
    ma5 = close.rolling(window=5).mean()
    ma10 = close.rolling(window=10).mean()
    ma20 = close.rolling(window=20).mean()
    ma60 = close.rolling(window=60).mean()

    # Condition 1: Bullish alignment (short > medium > long)
    alignment = (ma5 > ma10) & (ma10 > ma20) & (ma20 > ma60)

    # Condition 2: All MAs trending up (current > previous)
    ma5_up = ma5 > ma5.shift(5)
    ma10_up = ma10 > ma10.shift(5)
    ma20_up = ma20 > ma20.shift(5)
    ma60_up = ma60 > ma60.shift(5)
    all_up = ma5_up & ma10_up & ma20_up & ma60_up

    # Twist signal
    twist = alignment & all_up

    # Classify position: distance from ma60
    distance_from_ma60 = (close - ma60) / ma60 * 100

    # LOW-position twist: within 15% of ma60 (safer entry)
    low_position = twist & (distance_from_ma60 <= 15)

    # HIGH-position twist: >30% above ma60 (risky, might be trap)
    high_position = twist & (distance_from_ma60 > 30)

    # MID-position: between 15% and 30%
    mid_position = twist & (distance_from_ma60 > 15) & (distance_from_ma60 <= 30)

    return {
        "twist": twist,
        "low_position": low_position,
        "mid_position": mid_position,
        "high_position": high_position,
        "ma5": ma5,
        "ma10": ma10,
        "ma20": ma20,
        "ma60": ma60,
        "distance_pct": distance_from_ma60,
    }


@register_indicator("ZX_ABNORMAL", category="composite")
def detect_abnormal_movement(
    df: pd.DataFrame,
    volume_mult: float = 2.0,
    min_gain_pct: float = 3.0,
    lookback: int = 20,
) -> pd.Series:
    """Detect abnormal movement (异动) signal.

    From Z哥: "异动 = 突然放量，价随量升"
    Key characteristics:
    1. Sudden volume surge (>= volume_mult x recent average)
    2. Price rises with volume (价随量升)
    3. Near or below 60-day MA (60日线底下或者附近的异动越强，后面空间更大)
    4. 60-day MA turning flat or up (黄线拐头)

    After abnormal movement, the subsequent "shrinking volume pullback"
    has判断 "floor price" value - this is where B1 opportunities emerge.
    """
    close = df["close"]
    open_ = df["open"]
    volume = df["vol"]

    # 60-day MA
    ma60 = close.rolling(window=60).mean()

    # Condition 1: Volume surge
    avg_volume = volume.rolling(window=lookback).mean()
    volume_surge = volume >= avg_volume * volume_mult

    # Condition 2: Price rises with volume (close > open, and gain >= min_gain_pct)
    gain_pct = (close - open_) / open_ * 100
    price_rises = (close > open_) & (gain_pct >= min_gain_pct)

    # Condition 3: Near or below 60-day MA (within 10% below or any above)
    near_ma60 = (close >= ma60 * 0.90) | (close >= ma60)

    # Condition 4: 60-day MA flat or turning up
    ma60_flat_or_up = ma60 >= ma60.shift(5)

    # Abnormal movement signal
    abnormal = volume_surge & price_rises & near_ma60 & ma60_flat_or_up

    return abnormal


@register_indicator("ZX_SINGLE_NEEDLE_20", category="composite")
def detect_single_needle_20(df: pd.DataFrame, n1: int = 5, n2: int = 60) -> pd.Series:
    """Single-needle below 20 (单针下20 / 补票战法核心信号).

    From Z哥's knowledge base - exact formula from 补票战法:
        短期 = 100*(CLOSE - LLV(LOW, N1))/(HHV(CLOSE, N1) - LLV(LOW, N1))
        长期 = 100*(CLOSE - LLV(LOW, N2))/(HHV(CLOSE, N2) - LLV(LOW, N2))

    Buy condition (补票信号):
        1. 长期 >= 80 for 5 consecutive days (长线5日内大于80)
        2. 长期 >= 99.99 today (长线今天等于100)
        3. 短期 >= 99.99 today (白线今天等于100)
        4. 短期 <= 20 yesterday (白线昨天小于等于20)

    This is the "deep V" reversal pattern - white line quickly V-bounces
    from below 20 to 100, while red line stays elevated (>80).
    """
    close = df["close"]
    low = df["low"]

    # Short-term (white) stochastic
    ll_n1 = low.rolling(window=n1).min()
    hh_n1 = close.rolling(window=n1).max()
    short_term = (close - ll_n1) / (hh_n1 - ll_n1) * 100

    # Long-term (red) stochastic
    ll_n2 = low.rolling(window=n2).min()
    hh_n2 = close.rolling(window=n2).max()
    long_term = (close - ll_n2) / (hh_n2 - ll_n2) * 100

    # Condition 1: Long-term >= 80 for 5 consecutive days
    long_above_80 = long_term >= 80
    long_5days = long_above_80.rolling(window=5).min().fillna(0).astype(bool)

    # Condition 2: Long-term >= 99.99 today
    long_near_100 = long_term >= 99.99

    # Condition 3: Short-term >= 99.99 today
    short_near_100 = short_term >= 99.99

    # Condition 4: Short-term <= 20 yesterday
    short_below_20_yesterday = short_term.shift(1) <= 20

    # Combined signal
    signal = long_5days & long_near_100 & short_near_100 & short_below_20_yesterday

    return signal


@register_indicator("ZX_PIT_TARGET", category="composite")
def calculate_pit_target(df: pd.DataFrame, lookback: int = 60) -> dict:
    """Pit strategy (坑口战法) - detect golden pit and calculate target price.

    From Z哥: "坑向上计算目标价位的公式 = 颈线 * 2 - 坑底"
    Or equivalently: Target = Neckline + (Neckline - PitBottom)

    Golden pit characteristics:
    1. Price falls significantly from a neckline level (at least 20% decline)
    2. Forms a bottom and stabilizes (consolidation at pit bottom)
    3. Volume dries up at the bottom (缩量企稳)
    4. When price breaks above neckline, target is calculated

    Returns dict with pit detection signals and target prices.
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["vol"]

    # Find neckline (recent significant high before decline)
    recent_high = high.rolling(window=lookback).max()
    recent_low = low.rolling(window=lookback).min()

    # Decline from high (at least 20% to be considered a pit)
    decline_pct = (recent_high - close) / recent_high * 100
    in_pit = decline_pct >= 20

    # Volume dries up at bottom (volume < 50% of recent average)
    avg_volume = volume.rolling(window=20).mean()
    volume_dry = volume < avg_volume * 0.5

    # Pit bottom stabilization: price near recent low + volume dry
    near_bottom = (close <= recent_low * 1.05) & (close >= recent_low * 0.98)
    stabilization = near_bottom & volume_dry

    # Breakout above neckline
    above_neckline = close > recent_high.shift(5) * 0.98  # Allow small tolerance

    # Calculate target price: Target = Neckline * 2 - PitBottom
    # Use the lowest point in the pit as pit_bottom
    pit_bottom = recent_low
    neckline = recent_high.shift(lookback // 2)  # High before the pit
    target_price = neckline * 2 - pit_bottom

    # Current progress toward target
    progress_pct = (close - pit_bottom) / (target_price - pit_bottom) * 100
    progress_pct = progress_pct.where(target_price > pit_bottom, 0)

    # Pit signal: in pit area + stabilization detected
    pit_signal = in_pit & stabilization

    return {
        "in_pit": in_pit,
        "stabilization": stabilization,
        "pit_signal": pit_signal,
        "above_neckline": above_neckline,
        "neckline": neckline,
        "pit_bottom": pit_bottom,
        "target_price": target_price,
        "progress_pct": progress_pct,
    }


@register_indicator("ZX_THREE_WAVES", category="composite")
def detect_three_waves(df: pd.DataFrame, lookback: int = 60) -> dict:
    """Three-wave theory (三波理论) detector.

    From Z哥's knowledge base:
    1. 建仓波 (Build Wave): Bottom rises with continuous volume,
       cumulative gain 25-50%, no limit-up boards preferred
    2. 拉升波 (Pull Wave): Quickly脱离建仓成本区,
       first B1 after pull wave should be avoided
    3. 冲刺波 (Sprint Wave): Final large-scale rise,
       do not touch after sprint wave

    Key filtering rules:
    - First B1 after pull wave: avoid (risky)
    - After sprint wave: do not enter
    - One-wave flow (一波流): no clear build/pull structure, avoid

    Returns dict with wave phase classification and trading signals.
    """
    close = df["close"]
    volume = df["vol"]

    # Calculate cumulative gain in lookback window
    start_price = close.shift(lookback)
    cumulative_gain = (close - start_price) / start_price * 100

    # Calculate average volume vs current volume
    avg_volume = volume.rolling(window=20).mean()
    volume_ratio = volume / avg_volume

    # Build wave detection: bottom area + significant volume + moderate gain
    # Price near recent lows but starting to rise
    recent_low = close.rolling(window=lookback).min()
    near_bottom = close <= recent_low * 1.15  # Within 15% of bottom

    # Significant volume during build phase (avg volume > 1.5x)
    high_volume_period = avg_volume > volume.shift(20).rolling(window=20).mean() * 1.5

    # Build wave: near bottom + cumulative gain 15-50% + volume confirmation
    build_wave = near_bottom & (cumulative_gain >= 15) & (cumulative_gain <= 50) & high_volume_period

    # Pull wave: after build, rapid rise (>20% in short time), not near bottom anymore
    short_gain = (close - close.shift(10)) / close.shift(10) * 100
    rapid_rise = short_gain >= 20
    pull_wave = (~near_bottom) & rapid_rise & (cumulative_gain >= 20) & (cumulative_gain < 50)

    # Sprint wave: after significant rise, parabolic move
    sprint_wave = (cumulative_gain >= 50) & (short_gain >= 15)

    # One-wave flow detection: no clear volume structure, straight rise
    # Characterized by: low volume during rise, no consolidation
    one_wave = (cumulative_gain >= 30) & (~high_volume_period) & (volume_ratio < 1.2)

    # Phase classification
    phase = pd.Series("unknown", index=df.index)
    phase[build_wave] = "build"
    phase[pull_wave & ~sprint_wave] = "pull"
    phase[sprint_wave] = "sprint"
    phase[one_wave] = "one_wave"

    # Trading signals
    # Avoid first B1 after pull wave
    after_pull = phase.shift(1) == "pull"
    avoid_b1 = after_pull & (phase == "pull")

    # Do not enter after sprint wave
    after_sprint = phase.shift(1) == "sprint"
    no_enter = after_sprint

    return {
        "phase": phase,
        "build_wave": build_wave,
        "pull_wave": pull_wave,
        "sprint_wave": sprint_wave,
        "one_wave": one_wave,
        "avoid_b1": avoid_b1,
        "no_enter": no_enter,
    }


@register_indicator("ZX_TWO_THIRTY", category="composite")
def validate_two_thirty_rule(
    df: pd.DataFrame,
    max_gain_pct: float = 30.0,
    max_turnover_pct: float = 30.0,
    lookback: int = 20,
) -> pd.Series:
    """Two-30% rule validator (两个30%原则).

    From Z哥's knowledge base (TANGOO article):
    "相对安全的区间是：前期放量的三根中大阳线，累计换手率不超过30%，
     且建仓期间绝对涨幅不超过30%"

    This rule filters out stocks that have risen too much or turned over
    too much during the accumulation phase, which indicates potential
    distribution rather than accumulation.

    Args:
        max_gain_pct: Maximum allowed cumulative gain (default 30%)
        max_turnover_pct: Maximum allowed cumulative turnover (default 30%)
        lookback: Window to check for the rule

    Returns:
        Boolean series: True if stock passes the two-30% rule
    """
    close = df["close"]
    volume = df["vol"]

    # Calculate cumulative gain in lookback window
    start_price = close.shift(lookback)
    cumulative_gain = (close - start_price) / start_price * 100

    # Calculate cumulative turnover (need total shares for true turnover)
    # Using volume ratio as proxy if true turnover data not available
    # Cumulative volume / average daily volume
    cumulative_volume = volume.rolling(window=lookback).sum()
    avg_daily_volume = volume.rolling(window=lookback).mean()
    turnover_proxy = cumulative_volume / avg_daily_volume

    # Normalize turnover_proxy to approximate percentage
    # Assuming avg daily volume represents ~1-2% of float
    # So cumulative_volume / float ≈ turnover_pct
    # Using a heuristic: if volume data shows 3 big volume days with 10% each = 30%
    # This is a simplified proxy - true implementation needs float data
    cumulative_turnover_pct = turnover_proxy * 1.5  # Rough heuristic

    # Check if both conditions are met
    gain_ok = cumulative_gain <= max_gain_pct
    turnover_ok = cumulative_turnover_pct <= max_turnover_pct

    # Combined: both conditions must be satisfied
    return gain_ok & turnover_ok
