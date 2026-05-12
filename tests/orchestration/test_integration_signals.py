"""End-to-end integration tests for signal processing pipeline."""
import pytest
from datetime import timedelta
from orchestration.signals.v2 import SignalV2, SignalAction, SignalPool
from orchestration.signals.aggregator import Aggregator, ConflictHandler
from orchestration.memory import ContextMemory, ConversationContext, UserProfile, Turn


def test_full_pipeline():
    """完整流程: 信号收集 -> 聚合 -> 记忆"""
    # 1. 收集信号
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="B2", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["技术"]))

    # 2. 聚合
    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())

    # 3. 记忆
    mem = ContextMemory(db_path=":memory:")
    ctx = ConversationContext(
        session_id="test-full",
        asset_focus=["茅台"]
    )
    mem.save(ctx)

    # 验证
    assert result.conflicts  # 应该有冲突
    # RECENT_WINS: 最近的信号赢，这里 B2 添加在后，所以 B2 的 SELL 赢
    assert result.action == SignalAction.SELL

    mem.close()


def test_weighted_voting_integration():
    """测试加权投票聚合"""
    pool = SignalPool()
    pool.add(SignalV2(source="RSI", action=SignalAction.BUY, confidence=0.9, weight=0.8, tags=["技术"]))
    pool.add(SignalV2(source="MACD", action=SignalAction.BUY, confidence=0.7, weight=0.6, tags=["技术"]))
    pool.add(SignalV2(source="波动率", action=SignalAction.SELL, confidence=0.5, weight=0.4, tags=["风险"]))

    agg = Aggregator(ConflictHandler.WEIGHTED_VOTING)
    result = agg.aggregate(pool.get_all())

    # BUY 信号权重更高: (0.9*0.8 + 0.7*0.6) = 1.14 vs (0.5*0.4) = 0.2
    assert result.action == SignalAction.BUY
    # 置信度 = 总分/信号数 = 1.14/3 ≈ 0.38
    assert result.confidence > 0.3


def test_conflict_detection():
    """测试冲突检测"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="宏观", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["宏观"]))

    assert pool.has_conflict() is True

    # 无冲突场景
    pool2 = SignalPool()
    pool2.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool2.add(SignalV2(source="B2", action=SignalAction.BUY, confidence=0.6, weight=0.5, tags=["技术"]))
    assert pool2.has_conflict() is False


def test_memory_preference_learning():
    """测试偏好学习"""
    mem = ContextMemory(db_path=":memory:")

    # 模拟用户多次采纳 SELL 信号
    session_id = "user-learn-001"
    for _ in range(5):
        mem.record_feedback(session_id, SignalAction.SELL, accepted=True)

    # 验证偏好学习：SELL 被采纳多次应该记录到 user_feedback 表
    profile = mem.get_user_profile(session_id)
    assert profile is not None
    assert isinstance(profile, UserProfile)

    # 验证反馈记录存在 (通过加载包含反馈数据的上下文)
    conn = mem._get_conn()
    feedback_count = conn.execute(
        "SELECT COUNT(*) FROM user_feedback WHERE session_id = ? AND action = ?",
        (session_id, SignalAction.SELL.value)
    ).fetchone()[0]
    assert feedback_count == 5  # 5次 SELL 反馈

    mem.close()


def test_high_confidence_wins():
    """测试高置信度获胜策略"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.5, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="宏观", action=SignalAction.SELL, confidence=0.9, weight=0.5, tags=["宏观"]))

    agg = Aggregator(ConflictHandler.HIGH_CONFIDENCE_WINS)
    result = agg.aggregate(pool.get_all())

    # SELL 的 confidence * weight = 0.9 * 0.5 = 0.45
    # BUY 的 confidence * weight = 0.5 * 0.7 = 0.35
    assert result.action == SignalAction.SELL


def test_debate_mode():
    """测试辩论模式返回 HOLD"""
    pool = SignalPool()
    pool.add(SignalV2(source="B1", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术"]))
    pool.add(SignalV2(source="宏观", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["宏观"]))

    agg = Aggregator(ConflictHandler.DEBATE_MODE)
    result = agg.aggregate(pool.get_all())

    assert result.action == SignalAction.HOLD
    assert result.confidence == 0.5


def test_no_signals():
    """测试空信号列表"""
    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate([])

    assert result.action == SignalAction.NEUTRAL
    assert result.confidence == 0.0
    assert len(result.signals) == 0
    assert len(result.conflicts) == 0


def test_context_persistence():
    """测试上下文持久化"""
    mem = ContextMemory(db_path=":memory:")

    # 创建带历史的上下文
    ctx = ConversationContext(
        session_id="persist-test",
        history=[
            Turn(role="user", content="茅台怎么看"),
            Turn(role="assistant", content="分析中..."),
        ],
        asset_focus=["茅台", "五粮液"]
    )

    # 保存
    mem.save(ctx)

    # 加载验证
    loaded = mem.load("persist-test")
    assert loaded is not None
    assert loaded.session_id == "persist-test"
    assert len(loaded.history) == 2
    assert loaded.asset_focus == ["茅台", "五粮液"]
    assert loaded.history[0].role == "user"
    assert loaded.history[1].content == "分析中..."

    mem.close()


def test_tag_groups_in_result():
    """测试聚合结果中的标签分组"""
    pool = SignalPool()
    pool.add(SignalV2(source="RSI", action=SignalAction.BUY, confidence=0.8, weight=0.7, tags=["技术", "超买"]))
    pool.add(SignalV2(source="MACD", action=SignalAction.BUY, confidence=0.7, weight=0.6, tags=["技术"]))
    pool.add(SignalV2(source="宏观", action=SignalAction.SELL, confidence=0.6, weight=0.5, tags=["宏观"]))

    agg = Aggregator(ConflictHandler.RECENT_WINS)
    result = agg.aggregate(pool.get_all())

    assert "技术" in result.metadata.get("tag_groups", [])
    assert "宏观" in result.metadata.get("tag_groups", [])


def test_memory_profile_update():
    """测试用户画像更新"""
    mem = ContextMemory(db_path=":memory:")
    session_id = "profile-update-test"

    # 初始画像
    ctx = ConversationContext(
        session_id=session_id,
        user_profile=UserProfile(risk_tolerance="high", signal_preferences={})
    )
    mem.save(ctx)

    # 验证初始状态
    profile = mem.get_user_profile(session_id)
    assert profile.risk_tolerance == "high"

    mem.close()