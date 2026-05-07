"""Zettaranc trading system indicators.

Indicators derived from Z哥's trading system:
- Double-line system (white/yellow lines, golden/dead cross)
- BBI (Bull and Bear Index)
- KDJ with B1 signal detection
- Brick chart (砖型图)
- Single-needle code (单针代码)
- Single-needle below 20 (单针下20 / 补票战法)
- Violent K detection (暴力K)
- Breathing structure (呼吸结构)
- B2 breakthrough
- Five-point scoring
- SB1 fake-fall
- S1 top warning
- Half-position release
- Ultimate B1 screener
- Super B1 (超级B1 - advanced shakeout signal)
- N-structure detection (N型结构)
- Twist (扭一扭 - MA bullish alignment)
- Abnormal movement (异动检测)
- Pit target (坑口战法 - 黄金坑识别与目标价)
- Three waves (三波理论 - 建仓/拉升/冲刺波)
- Two-thirty rule (两个30%原则)
"""
from quant.indicators.zettaranc import composite
