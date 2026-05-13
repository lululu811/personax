#!/usr/bin/env python3
"""Demo: Signal Review System - 异步事件驱动的信号回顾机制"""

from datetime import datetime, timedelta
from orchestration.review.event_bus import EventBus, emit as emit_signal
from orchestration.review.review_service import ReviewService
from orchestration.review.models import SignalEvent, SignalAction

def demo_event_bus():
    print("=" * 60)
    print("Demo 1: EventBus 事件总线 (Fire & Forget)")
    print("=" * 60)

    bus = EventBus()
    received = []

    def handler(event):
        received.append(event)
        print(f"  [收到事件] {event.source}: {event.action.value} @ {event.price}")

    bus.subscribe("signal", handler)

    # 发射多个事件
    events = [
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=6),
            source="B1策略",
            action=SignalAction.BUY,
            confidence=0.85,
            reason="砖块突破，趋势确认",
            price=1800.0,
            asset="600519",
            tags=["技术", "趋势"]
        ),
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=5),
            source="RSI",
            action=SignalAction.BUY,
            confidence=0.7,
            reason="RSI < 30，超卖区域",
            price=1780.0,
            asset="600519",
            tags=["动量"]
        ),
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=4),
            source="MACD",
            action=SignalAction.SELL,
            confidence=0.65,
            reason="MACD 死叉，趋势转弱",
            price=1820.0,
            asset="600519",
            tags=["趋势", "动量"]
        ),
    ]

    print("\n发射事件:")
    for event in events:
        bus.emit("signal", event)
        print(f"  [发射] {event.source}")

    # 等待异步处理
    import time
    time.sleep(0.5)

    print(f"\n共收到 {len(received)} 个事件")

    return received


def demo_review_service():
    print("\n" + "=" * 60)
    print("Demo 2: ReviewService 回顾服务")
    print("=" * 60)

    # 创建服务（使用内存数据库）
    service = ReviewService(db_path=":memory:")

    # 添加一些历史信号
    signals = [
        # 6天前的 BUY 信号 - 事后价格上涨 = 正确
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=6),
            source="B1策略",
            action=SignalAction.BUY,
            confidence=0.85,
            reason="砖块突破",
            price=1800.0,
            asset="600519",
            tags=["技术"]
        ),
        # 5天前的 BUY 信号 - 事后价格下跌 = 错误
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=5),
            source="RSI",
            action=SignalAction.BUY,
            confidence=0.7,
            reason="RSI 超卖",
            price=1780.0,
            asset="600519",
            tags=["动量"]
        ),
        # 4天前的 SELL 信号 - 事后价格下跌 = 正确
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=4),
            source="MACD",
            action=SignalAction.SELL,
            confidence=0.65,
            reason="MACD 死叉",
            price=1820.0,
            asset="600519",
            tags=["趋势"]
        ),
    ]

    print("\n添加历史信号:")
    for s in signals:
        service.on_signal(s)
        print(f"  + {s.source}: {s.action.value} @ {s.price}")

    # 模拟事后价格验证
    print("\n模拟事后价格验证:")
    print("  B1策略 BUY @ 1800 → 事后 1850 (涨) = correct")
    print("  RSI BUY @ 1780 → 事后 1750 (跌) = incorrect")
    print("  MACD SELL @ 1820 → 事后 1780 (跌) = correct")

    # 执行每周回顾
    print("\n执行每周回顾:")
    result = service.review_weekly()

    print(f"\n回顾报告:")
    print(result.report)

    print("\n权重调整建议:")
    for source, adjustment in result.weight_adjustments.items():
        sign = "+" if adjustment > 0 else ""
        print(f"  {source}: {sign}{adjustment:.2f}")


def demo_full_pipeline():
    print("\n" + "=" * 60)
    print("Demo 3: 完整 Pipeline")
    print("=" * 60)

    # 1. EventBus + ReviewService 联动
    bus = EventBus()
    service = ReviewService(db_path=":memory:")

    def signal_handler(event):
        service.on_signal(event)

    bus.subscribe("signal", signal_handler)

    # 2. 模拟 Engine 发射事件
    print("\n[模拟] Engine.execute() 发射信号事件:")

    new_signals = [
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=3),
            source="KDJ",
            action=SignalAction.BUY,
            confidence=0.8,
            reason="KDJ 金叉",
            price=1790.0,
            asset="000001",
            tags=["技术", "动量"]
        ),
        SignalEvent(
            timestamp=datetime.now() - timedelta(days=2),
            source="布林带",
            action=SignalAction.SELL,
            confidence=0.6,
            reason="价格触及上轨",
            price=1810.0,
            asset="000001",
            tags=["技术", "波动"]
        ),
    ]

    for signal in new_signals:
        emit_signal("signal", signal)
        print(f"  [发射] {signal.source}: {signal.action.value}")

    import time
    time.sleep(0.3)

    # 3. 验证存储
    unevaluated = service.signal_history.get_unevaluated()
    print(f"\n[验证] 共存储 {len(unevaluated)} 个未评估信号")

    # 4. 执行回顾
    result = service.review_monthly()
    print(f"\n[回顾] 月度回顾结果:")
    print(f"  总信号数: {result.total_signals}")
    print(f"  正确: {result.correct}")
    print(f"  错误: {result.incorrect}")
    print(f"  准确率: {result.accuracy*100:.1f}%")


def demo_cli():
    print("\n" + "=" * 60)
    print("Demo 4: CLI 使用方式")
    print("=" * 60)

    print("""
# 每周回顾
python -m orchestration.review.cli weekly

# 每月回顾
python -m orchestration.review.cli monthly

# 指定数据库路径
python -m orchestration.review.cli weekly --db-path ~/.personax/my_review.db
""")


if __name__ == "__main__":
    demo_event_bus()
    demo_review_service()
    demo_full_pipeline()
    demo_cli()

    print("\n" + "=" * 60)
    print("Demo 完成!")
    print("=" * 60)
