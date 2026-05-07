"""Pattern Strategies - Zettaranc specific pattern detections.

These are Z哥-specific patterns that are harder to generalize.

Patterns:
- Double Ponytail (双马尾战法): Two long-shadow volume candles at bottom
- Three Outside Three (三外有三): Three consecutive big gains then B1
- Top Windmill (顶部大风车): Huge volume + long shadows at high
- Three Quarters Volume (四分之三阴量线): Post-breakout fake breakout
- Fake Bearish (假阴真阳): Bearish look but actually bullish
- Double Gun (双枪战法): Two volume bullish with shrinking middle
- Buy Exhaustion (买盘枯竭): Small bullish + shrinking volume after rise
- Long Shadow Short Volume (长阴短柱): Long bearish with low volume

Usage:
    from personas.zettaranc.strategies.patterns import (
        DoublePonytailStrategy,
        ThreeOutsideThreeStrategy,
        TopWindmillStrategy,
        ThreeQuartersVolumeStrategy,
        FakeBearishStrategy,
        DoubleGunStrategy,
        BuyExhaustionStrategy,
        LongShadowShortVolumeStrategy,
    )
"""

from dataclasses import dataclass
import pandas as pd

from personas.zettaranc.strategies.b1 import StrategySignal


@dataclass
class DoublePonytailStrategy:
    """Double ponytail - two long-shadow volume candles."""

    name = "double_ponytail"

    def detect(
        self,
        df: pd.DataFrame,
        shadow_ratio: float = 2.0,
        volume_mult: float = 1.5,
        max_distance: int = 5,
        min_decline_pct: float = 15.0,
    ) -> StrategySignal:
        """Detect double ponytail pattern."""
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        close = df["close"]
        volume = df["vol"]

        body = abs(close - open_)
        upper_shadow = high - close.where(close >= open_, open_)
        long_shadow = upper_shadow >= body * shadow_ratio

        avg_volume = volume.rolling(window=20).mean()
        high_volume = volume >= avg_volume * volume_mult
        ponytail = long_shadow & high_volume

        # Need two ponytails close together
        ponytail_indices = ponytail[ponytail].index
        has_pair = pd.Series(False, index=df.index)

        for idx in ponytail_indices:
            idx_pos = df.index.get_loc(idx)
            for offset in range(1, max_distance + 1):
                if idx_pos - offset >= 0:
                    other_idx = df.index[idx_pos - offset]
                    if ponytail.loc[other_idx]:
                        has_pair.loc[idx] = True
                        break
                if idx_pos + offset < len(df):
                    other_idx = df.index[idx_pos + offset]
                    if ponytail.loc[other_idx]:
                        has_pair.loc[idx] = True
                        break

        # At bottom
        recent_high = high.rolling(window=40).max()
        decline_from_high = (recent_high - close) / recent_high * 100
        at_bottom = decline_from_high >= min_decline_pct

        signal = has_pair & at_bottom

        if signal.iloc[-1]:
            return StrategySignal(
                action="buy",
                confidence=0.65,
                reason="双马尾战法: 两根上影放量K线在底部，主力震仓",
                metadata={"at_bottom": at_bottom.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无双马尾信号",
            metadata={},
        )


@dataclass
class ThreeOutsideThreeStrategy:
    """Three outside three - three big gains then B1."""

    name = "three_outside_three"

    def detect(
        self,
        df: pd.DataFrame,
        min_gain_pct: float = 9.0,
        pullback_lookback: int = 10,
    ) -> StrategySignal:
        """Detect three outside three pattern."""
        close = df["close"]
        high = df["high"]
        low = df["low"]

        gain_pct = (close - close.shift(1)) / close.shift(1) * 100
        three_up = (
            (gain_pct >= min_gain_pct)
            & (gain_pct.shift(1) >= min_gain_pct)
            & (gain_pct.shift(2) >= min_gain_pct)
        )

        recent_high_before = high.rolling(window=30).max().shift(3)
        decline_before = (recent_high_before - close.shift(3)) / recent_high_before * 100
        had_decline = decline_before >= 20

        pullback_zone = three_up.rolling(window=pullback_lookback).max().shift(-pullback_lookback).fillna(False)

        # B1 signal
        lowest_low = low.rolling(window=9).min()
        highest_high = high.rolling(window=9).max()
        rsv = (close - lowest_low) / (highest_high - lowest_low) * 100
        rsv = rsv.fillna(0)
        k = rsv.rolling(window=3).mean()
        d = k.rolling(window=3).mean()
        j = 3 * k - 2 * d
        b1_signal = j < 13

        signal = pullback_zone.astype(bool) & b1_signal.astype(bool) & had_decline.astype(bool)

        if signal.iloc[-1]:
            return StrategySignal(
                action="buy",
                confidence=0.7,
                reason="三外有三战法: 三连板后回调B1，短庄机会",
                metadata={"had_decline": had_decline.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无三外有三信号",
            metadata={},
        )


@dataclass
class TopWindmillStrategy:
    """Top windmill - top reversal warning."""

    name = "top_windmill"

    def detect(
        self,
        df: pd.DataFrame,
        volume_mult: float = 2.5,
        shadow_min_pct: float = 2.0,
        lookback: int = 20,
    ) -> StrategySignal:
        """Detect top windmill pattern."""
        close = df["close"]
        high = df["high"]
        low = df["low"]
        open_ = df["open"]
        volume = df["vol"]

        bearish = close < open_
        avg_volume = volume.rolling(window=lookback).mean()
        huge_volume = volume >= avg_volume * volume_mult

        body = abs(close - open_)
        upper_shadow = high - open_
        lower_shadow = close - low
        long_upper = (upper_shadow / body) >= shadow_min_pct
        long_lower = (lower_shadow / body) >= shadow_min_pct
        long_shadows = long_upper & long_lower

        recent_high = high.rolling(window=lookback).max()
        near_high = close >= recent_high * 0.85

        signal = bearish & huge_volume & long_shadows & near_high

        if signal.iloc[-1]:
            return StrategySignal(
                action="warning",
                confidence=0.75,
                reason="顶部大风车: 放量长影在高位，见顶减仓",
                metadata={"near_high": near_high.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无顶部大风车信号",
            metadata={},
        )


@dataclass
class ThreeQuartersVolumeStrategy:
    """Three quarters volume - post-breakout fake breakout."""

    name = "three_quarters"

    def detect(
        self,
        df: pd.DataFrame,
        breakout_gain_pct: float = 4.0,
        volume_ratio: float = 0.75,
    ) -> StrategySignal:
        """Detect three quarters volume pattern."""
        close = df["close"]
        open_ = df["open"]
        volume = df["vol"]

        prev_gain = (close.shift(1) - close.shift(2)) / close.shift(2) * 100
        was_breakout = prev_gain >= breakout_gain_pct

        today_bearish = close < open_
        vol_condition = volume >= volume.shift(1) * volume_ratio

        signal = was_breakout & today_bearish & vol_condition

        if signal.iloc[-1]:
            return StrategySignal(
                action="warning",
                confidence=0.7,
                reason="四分之三阴量线: 突破后放量阴线，可能是假突破",
                metadata={"was_breakout": was_breakout.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无四分之三阴量信号",
            metadata={},
        )


@dataclass
class FakeBearishStrategy:
    """Fake bearish - bullish disguised as bearish."""

    name = "fake_bearish"

    def detect(
        self,
        df: pd.DataFrame,
        min_gain_pct: float = 0.0,
    ) -> StrategySignal:
        """Detect fake bearish pattern."""
        close = df["close"]
        open_ = df["open"]

        bearish_look = close < open_
        actual_rise = close > close.shift(1)
        gain_vs_prev = (close - close.shift(1)) / close.shift(1) * 100
        min_rise = gain_vs_prev >= min_gain_pct

        signal = bearish_look & actual_rise & min_rise

        if signal.iloc[-1]:
            return StrategySignal(
                action="buy",
                confidence=0.6,
                reason="假阴真阳: 阴线外观但实际上涨，主力洗盘续涨",
                metadata={"gain_pct": gain_vs_prev.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无假阴真阳信号",
            metadata={},
        )


@dataclass
class DoubleGunStrategy:
    """Double gun - two volume bullish with shrinking middle."""

    name = "double_gun"

    def detect(
        self,
        df: pd.DataFrame,
        volume_mult: float = 1.5,
        max_middle_days: int = 5,
        min_gain_pct: float = 3.0,
    ) -> StrategySignal:
        """Detect double gun pattern."""
        close = df["close"]
        open_ = df["open"]
        volume = df["vol"]

        avg_volume = volume.rolling(window=20).mean()
        bullish = close > open_
        high_volume = volume >= avg_volume * volume_mult
        gain_pct = (close - open_) / open_ * 100
        big_gain = gain_pct >= min_gain_pct

        first_gun = bullish & high_volume & big_gain

        signal = pd.Series(False, index=df.index)
        for i in range(max_middle_days + 2, len(df)):
            idx = df.index[i]
            if not (bullish.iloc[i] and high_volume.iloc[i] and big_gain.iloc[i]):
                continue

            found_first_gun = False
            for j in range(1, max_middle_days + 2):
                back_idx = i - j
                if back_idx < 0:
                    break
                if first_gun.iloc[back_idx]:
                    middle_start = back_idx + 1
                    middle_end = i
                    if middle_end <= middle_start:
                        found_first_gun = True
                        break
                    middle_volume = volume.iloc[middle_start:middle_end]
                    middle_avg_vol = middle_volume.mean()
                    if middle_avg_vol < volume.iloc[back_idx] * 0.8:
                        found_first_gun = True
                        break

            if found_first_gun:
                signal.iloc[i] = True

        if signal.iloc[-1]:
            return StrategySignal(
                action="buy",
                confidence=0.7,
                reason="双枪战法: 两根放量阳柱夹缩量阴线，箭在弦上",
                metadata={"signal": True},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无双枪信号",
            metadata={},
        )


@dataclass
class BuyExhaustionStrategy:
    """Buy exhaustion - shrinking volume after rise."""

    name = "buy_exhaustion"

    def detect(
        self,
        df: pd.DataFrame,
        volume_shrink_pct: float = 0.5,
        lookback: int = 10,
        min_rise_pct: float = 20.0,
    ) -> StrategySignal:
        """Detect buy exhaustion pattern."""
        close = df["close"]
        open_ = df["open"]
        volume = df["vol"]

        start_price = close.shift(lookback)
        cumulative_gain = (close - start_price) / start_price * 100
        has_risen = cumulative_gain >= min_rise_pct

        gain_pct = (close - open_) / open_ * 100
        small_bullish = (close > open_) & (gain_pct < 2.0)

        avg_volume = volume.rolling(window=lookback).mean()
        volume_shrink = volume <= avg_volume * volume_shrink_pct

        signal = has_risen & small_bullish & volume_shrink

        if signal.iloc[-1]:
            return StrategySignal(
                action="warning",
                confidence=0.65,
                reason="买盘枯竭: 上涨后缩量小阳，动能不足",
                metadata={"cumulative_gain": cumulative_gain.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无买盘枯竭信号",
            metadata={},
        )


@dataclass
class LongShadowShortVolumeStrategy:
    """Long shadow short volume - main force washout."""

    name = "long_shadow_short"

    def detect(
        self,
        df: pd.DataFrame,
        body_pct_threshold: float = 2.0,
        volume_ratio: float = 0.8,
    ) -> StrategySignal:
        """Detect long shadow short volume pattern."""
        close = df["close"]
        open_ = df["open"]
        volume = df["vol"]

        bearish = close < open_
        decline_pct = (open_ - close) / open_ * 100
        significant_decline = decline_pct >= body_pct_threshold

        avg_volume = volume.rolling(window=20).mean()
        low_volume = volume <= avg_volume * volume_ratio

        signal = bearish & significant_decline & low_volume

        if signal.iloc[-1]:
            return StrategySignal(
                action="buy",
                confidence=0.7,
                reason="长阴短柱: 阴线长但量小，主力洗盘未出货",
                metadata={"decline_pct": decline_pct.iloc[-1]},
            )

        return StrategySignal(
            action="hold",
            confidence=0.0,
            reason="无长阴短柱信号",
            metadata={},
        )
