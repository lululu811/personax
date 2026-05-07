"""Pattern detection indicators from Zettaranc trading system."""
import pandas as pd
from quant.registry import register_indicator


@register_indicator("ZX_VIOLENT_K", category="pattern")
def detect_violent_k(
    df: pd.DataFrame,
    volume_mult: float = 2.0,
    lookback: int = 20,
    min_body_pct: float = 3.0,
) -> pd.Series:
    """Detect Violent K (暴力K) signals.

    A Violent K must satisfy three conditions simultaneously:
    1. Position: At bottom (sufficient decline from recent highs)
    2. Suddenness: Breaks previous K-line rhythm (significantly different)
    3. Volume: At least `volume_mult` times the average volume of last `lookback` days

    Args:
        df: DataFrame with open, high, low, close, vol columns
        volume_mult: Volume multiplier threshold (default 2.0 for double volume)
        lookback: Days to calculate average volume
        min_body_pct: Minimum body size as percentage of previous close

    Returns:
        Series of boolean signals
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]
    open_ = df["open"]
    volume = df["vol"]

    # 1. Position: recent decline from highs
    recent_high = high.rolling(window=lookback * 2).max()
    decline_from_high = (recent_high - close) / recent_high * 100
    at_bottom = decline_from_high >= 15  # At least 15% decline

    # 2. Body size
    body = abs(close - open_)
    body_pct = body / close.shift(1) * 100
    large_body = body_pct >= min_body_pct
    bullish = close > open_

    # 3. Volume surge
    avg_volume = volume.rolling(window=lookback).mean()
    volume_surge = volume >= avg_volume * volume_mult

    # Combined signal (all three must be true)
    return at_bottom & large_body & bullish & volume_surge


@register_indicator("ZX_BRICK_CHART", category="pattern")
def calculate_brick_chart(df: pd.DataFrame) -> dict:
    """Zettaranc brick chart (砖型图) indicator.

    Based on 4-day high/low range, similar to Williams %R but customized:
        VAR1 = (HHV(HIGH,4) - CLOSE) / (HHV(HIGH,4) - LLV(LOW,4)) * 100 - 90
        VAR2 = SMA(VAR1, 4, 1) + 100
        VAR3 = (CLOSE - LLV(LOW,4)) / (HHV(HIGH,4) - LLV(LOW,4)) * 100
        VAR4 = SMA(VAR3, 6, 1)
        VAR5 = SMA(VAR4, 6, 1) + 100
        VAR6 = VAR5 - VAR2
        Brick = IF(VAR6 > 4, VAR6 - 4, 0)

    Red brick (rising): current brick > previous brick
    Green brick (falling): current brick < previous brick

    Sell rules (DSZ):
        - Count 4 red bricks -> reduce position by half
        - Green brick appears -> exit immediately
        - If no rise by 9:37 next day -> exit
    """
    close = df["close"]
    high = df["high"]
    low = df["low"]

    hhv4 = high.rolling(window=4).max()
    llv4 = low.rolling(window=4).min()

    var1 = (hhv4 - close) / (hhv4 - llv4) * 100 - 90
    var2 = var1.rolling(window=4).mean() + 100

    var3 = (close - llv4) / (hhv4 - llv4) * 100
    var4 = var3.rolling(window=6).mean()
    var5 = var4.rolling(window=6).mean() + 100

    var6 = var5 - var2
    brick = var6.where(var6 > 4, 0)

    # Detect red/green transitions
    brick_rising = brick > brick.shift(1)
    brick_falling = brick < brick.shift(1)

    # Count consecutive red bricks
    consecutive_red = brick_rising.astype(int).groupby(
        (brick_rising != brick_rising.shift(1)).cumsum()
    ).cumsum() * brick_rising

    # DSZ signals
    four_red_bricks = consecutive_red >= 4
    green_appears = brick_falling

    return {
        "brick": brick,
        "rising": brick_rising,
        "falling": brick_falling,
        "consecutive_red": consecutive_red,
        "four_red_signal": four_red_bricks,
        "green_exit": green_appears,
    }


@register_indicator("ZX_BREATHING", category="pattern")
def detect_breathing_structure(
    df: pd.DataFrame,
    volume_shrink_pct: float = 0.5,
    lookback: int = 5,
) -> pd.Series:
    """Detect breathing structure (呼吸结构) in N-shaped uptrend.

    Breathing = Exhale (放量上涨) -> Inhale (缩量回调) -> Exhale (再放量上涨)

    Key principle: In an N-shaped uptrend, look for volume shrinkage
    (缩量难作假 - volume shrinkage is hard to fake).

    Args:
        df: DataFrame with close, high, low, vol
        volume_shrink_pct: Volume must shrink to this ratio of previous wave
        lookback: Window to identify the structure

    Returns:
        Series with breathing phase labels:
            1 = exhale (放量上涨)
            -1 = inhale (缩量回调)
            0 = no clear structure
    """
    close = df["close"]
    volume = df["vol"]

    # Price direction
    price_up = close > close.shift(1)
    price_down = close < close.shift(1)

    # Volume relative to recent average
    vol_avg = volume.rolling(window=lookback).mean()
    vol_high = volume > vol_avg
    vol_low = volume < vol_avg * volume_shrink_pct

    # Phase detection
    exhale = price_up & vol_high      # 呼气: 放量上涨
    inhale = price_down & vol_low     # 吸气: 缩量回调

    # Label phases
    phase = pd.Series(0, index=df.index)
    phase[exhale] = 1
    phase[inhale] = -1

    return phase


@register_indicator("ZX_KEY_K_SCREENER", category="pattern")
def key_k_screener(
    df: pd.DataFrame,
    volume_mult: float = 2.0,
    min_gain_pct: float = 4.0,
    lookback_days: int = 10,
) -> pd.Series:
    """Key-K stock screener (关键K选股三步公式).

    Step 1: Within `lookback_days`, volume >= 2x avg AND gain >= 4%
    Step 2: Current day: volume shrinks AND gain < 4%
    Step 3: Manual filter (sector heat, position, internal赛马)

    This function implements Step 1 + 2 automatically.

    Returns:
        Boolean series: True if stock passes Step 1+2 screening
    """
    close = df["close"]
    volume = df["vol"]

    # Step 1: Within lookback_days, find days with volume surge + gain
    avg_vol = volume.rolling(window=lookback_days).mean()
    gain_pct = (close - close.shift(1)) / close.shift(1) * 100

    volume_surge = volume >= avg_vol * volume_mult
    big_gain = gain_pct >= min_gain_pct
    step1_day = volume_surge & big_gain

    # Check if any step1 day within lookback
    has_step1 = step1_day.rolling(window=lookback_days).max().fillna(0).astype(bool)

    # Step 2: Current day - volume shrinks, gain < 4%
    volume_shrink = volume < avg_vol
    small_gain = gain_pct < min_gain_pct
    step2 = volume_shrink & small_gain

    return has_step1 & step2
