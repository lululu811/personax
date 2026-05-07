"""Zettaranc trading system indicators.

Indicators derived from Z哥's trading system:
- Double-line system (white/yellow lines, golden/dead cross)
- BBI (Bull and Bear Index)
- KDJ with B1 signal detection
- RSI(3) with 20/80 boundaries
- Brick chart (砖型图)
- Single-needle code (单针代码)
- Single-needle below 20 (单针下20 / 补票战法)
- Violent K detection (暴力K)
- Breathing structure (呼吸结构)
- B2 breakthrough
- Five-point scoring (少妇战法V1.3)
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
- Double ponytail (双马尾战法)
- Three outside three (三外有三战法)
- Top windmill (顶部大风车)
- Three-quarters volume (四分之三阴量线 / 假突破识别)
- Fake bearish (假阴真阳 - 主力洗盘信号)
- Double gun (双枪战法 - 两根放量阳柱夹缩量阴线)
- Buy exhaustion (买盘枯竭 - 上涨动能衰竭)
- Long shadow short volume (长阴短柱 - 主力洗盘未出货)
"""
from quant.indicators.zettaranc import composite
