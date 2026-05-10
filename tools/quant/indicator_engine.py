"""IndicatorEngine - 统一指标计算链路

设计原则：
1. 数据只拉一次 —— 增量同步到 DuckDB
2. 指标计算只依赖数据库 —— 库里没有 → 触发同步 → 再计算
3. 指标结果入库 —— 每日指标快照存库，形成趋势可追溯

Usage:
    engine = IndicatorEngine()
    engine.ensure_data("300274")        # 确保数据库有最新数据
    engine.compute_and_save("300274")   # 计算所有指标并存库
    df = engine.get_indicators("300274") # 从库读取指标
"""

import sys
from datetime import datetime, timedelta
from typing import List, Optional

import pandas as pd

from data.db import Database
from data.sync import SyncEngine


class IndicatorEngine:
    def __init__(self, persona_name: str = "zettaranc"):
        self.db = Database()
        self.sync_engine = SyncEngine(persona_name=persona_name)

    def ensure_data(self, code: str, days: int = 120) -> pd.DataFrame:
        """确保数据库有指定股票的最新数据。

        流程：
        1. 查库看最新交易日期
        2. 如果数据旧或没有 → 调用 SyncEngine 增量同步
        3. 返回完整数据 DataFrame
        """
        # 检查库里有没有数据
        df = self.db.get_daily(code)
        last_date = self.db.get_last_trade_date(code, "daily_prices")

        # 如果没数据或数据超过 1 天没更新，触发同步
        need_sync = False
        if df.empty:
            need_sync = True
        elif last_date:
            # last_date 格式是 YYYYMMDD，需要比较
            last_dt = datetime.strptime(last_date, "%Y%m%d")
            days_ago = (datetime.now() - last_dt).days
            if days_ago > 1:
                need_sync = True

        if need_sync:
            count = self.sync_engine.sync_stock(code)
            total = sum(count.values()) if isinstance(count, dict) else 0
            if total > 0:
                print(f"📡 正在同步 {code} 数据... ({total} 条)")
            df = self.db.get_daily(code)

        return df.sort_values("trade_date").reset_index(drop=True)

    def compute_and_save(self, code: str, df: Optional[pd.DataFrame] = None) -> dict:
        """计算所有指标并存入数据库。

        流程：
        1. 确保有数据（调用 ensure_data）
        2. 计算所有指标（KDJ/MACD/BBI/双线/砖形图/量比...）
        3. 将最后一天的指标快照存入 daily_indicators 表
        4. 返回计算结果字典
        """
        if df is None:
            df = self.ensure_data(code)
        if df.empty:
            raise ValueError(f"No data for {code}")

        # 确保有 vol 列
        if "vol" not in df.columns and "volume" in df.columns:
            df["vol"] = df["volume"]

        # 导入所有指标（lazy import 避免循环依赖）
        from tools.quant.technical import kdj, macd, bbi, bollinger, atr, rsi_3, stochastic
        from tools.quant.technical.double_line import double_line
        from tools.quant.technical.brick_pattern import brick_pattern
        from tools.quant.technical.vol_ratio import vol_ratio

        # 计算所有指标
        kdj_r = kdj.compute(df)
        macd_r = macd.compute(df)
        bbi_r = bbi.compute(df)
        boll_r = bollinger.compute(df)
        atr_r = atr.compute(df)
        rsi_r = rsi_3.compute(df)
        stoch_r = stochastic.compute(df)
        dl_r = double_line.compute(df)
        brick_r = brick_pattern.compute(df)
        vr_r = vol_ratio.compute(df)

        # 提取最新一天的值
        latest_date = df["trade_date"].iloc[-1]
        if isinstance(latest_date, str):
            trade_date_str = latest_date
        else:
            trade_date_str = latest_date.strftime("%Y-%m-%d")

        def latest_val(series):
            """从 Series 中取最新值"""
            if isinstance(series, pd.Series):
                val = series.iloc[-1]
                return None if pd.isna(val) else round(float(val), 4)
            return series

        indicators = {
            # KDJ
            "k": latest_val(kdj_r.data.get("K")),
            "d": latest_val(kdj_r.data.get("D")),
            "j": latest_val(kdj_r.data.get("J")),
            # MACD
            "dif": latest_val(macd_r.data.get("dif")),
            "dea": latest_val(macd_r.data.get("dea")),
            "macd": latest_val(macd_r.data.get("macd")),
            # BBI
            "bbi": latest_val(bbi_r.data.get("bbi")),
            # RSI
            "rsi": latest_val(rsi_r.data.get("rsi_3")),
            # ATR
            "atr": latest_val(atr_r.data.get("atr")),
            "atr_pct": latest_val(atr_r.data.get("atr_pct")),
            # Bollinger
            "boll_upper": latest_val(boll_r.data.get("upper")),
            "boll_mid": latest_val(boll_r.data.get("mid")),
            "boll_lower": latest_val(boll_r.data.get("lower")),
            # Stochastic
            "stoch_white": latest_val(stoch_r.data.get("white")),
            "stoch_yellow": latest_val(stoch_r.data.get("yellow")),
            "stoch_purple": latest_val(stoch_r.data.get("purple")),
            "stoch_red": latest_val(stoch_r.data.get("red")),
            # Double Line
            "white_line": latest_val(dl_r.data.get("white")),
            "yellow_line": latest_val(dl_r.data.get("yellow")),
            # Brick Pattern
            "brick_pattern": "red" if brick_r.signals.get("red_brick") else "green" if brick_r.signals.get("green_brick") else "unknown",
            "brick_count": int(brick_r.data.get("brick_count", pd.Series()).iloc[-1]) if isinstance(brick_r.data.get("brick_count"), pd.Series) else 0,
            # Volume Ratio
            "vol_ratio": latest_val(vr_r.data.get("vol_ratio")),
        }

        # 存库
        self.db.save_indicators(code, trade_date_str, indicators, source="local")

        # 返回完整结果（含 signals）
        return {
            "date": trade_date_str,
            "indicators": indicators,
            "signals": {
                "kdj": kdj_r.signals,
                "macd": macd_r.signals,
                "bbi": bbi_r.signals,
                "bollinger": boll_r.signals,
                "atr": atr_r.signals,
                "rsi": rsi_r.signals,
                "stochastic": stoch_r.signals,
                "double_line": dl_r.signals,
                "brick_pattern": brick_r.signals,
                "vol_ratio": vr_r.signals,
            },
        }

    def get_indicators(self, code: str, limit: int = 30) -> pd.DataFrame:
        """从数据库读取已计算的指标。"""
        return self.db.get_indicators(code, limit=limit)

    def get_latest_signal(self, code: str, signal_name: str) -> dict:
        """获取指定股票最新某个信号。"""
        result = self.compute_and_save(code)
        all_signals = result["signals"]
        for category, signals in all_signals.items():
            if signal_name in signals:
                return {
                    "category": category,
                    "signal": signal_name,
                    "value": signals[signal_name],
                    "date": result["date"],
                }
        return {"error": f"Signal '{signal_name}' not found"}
