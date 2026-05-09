"""Integration tests for new architecture: tools/orchestration/personas.

Tests the complete flow from tools → strategies → orchestration.
"""

import pytest
import pandas as pd
import numpy as np
import os


class TestToolLayer:
    """Test tools/quant/technical/ layer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100)
        data = pd.DataFrame({
            'open': 100 + np.cumsum(np.random.randn(100) * 2),
            'high': 100 + np.cumsum(np.random.randn(100) * 2) + 3,
            'low': 100 + np.cumsum(np.random.randn(100) * 2) - 3,
            'close': 100 + np.cumsum(np.random.randn(100) * 2),
            'vol': np.random.randint(1000000, 10000000, 100),
        })
        data['high'] = data[['open', 'close', 'high']].max(axis=1) + 2
        data['low'] = data[['open', 'close', 'low']].min(axis=1) - 2
        return data

    def test_kdj_tool(self, sample_data):
        """Test KDJ tool computation."""
        from tools.quant.technical import kdj
        result = kdj.compute(sample_data)
        assert 'K' in result.data
        assert 'D' in result.data
        assert 'J' in result.data
        assert 'b1' in result.signals
        assert result.tool_name == 'kdj'

    def test_rsi_tool(self, sample_data):
        """Test RSI tool computation."""
        from tools.quant.technical import rsi_3
        result = rsi_3.compute(sample_data)
        assert 'rsi' in result.data
        assert 'oversold' in result.signals
        assert 'overbought' in result.signals

    def test_bbi_tool(self, sample_data):
        """Test BBI tool computation."""
        from tools.quant.technical import bbi
        result = bbi.compute(sample_data)
        assert 'bbi' in result.data
        assert 'above_bbi' in result.signals

    def test_macd_tool(self, sample_data):
        """Test MACD tool computation."""
        from tools.quant.technical import macd
        result = macd.compute(sample_data)
        assert 'dif' in result.data
        assert 'dea' in result.data
        assert 'macd' in result.data

    def test_stochastic_tool(self, sample_data):
        """Test Stochastic tool computation."""
        from tools.quant.technical import stochastic
        result = stochastic.compute(sample_data)
        assert 'short' in result.data
        assert 'medium' in result.data
        assert 'long' in result.data

    def test_bollinger_tool(self, sample_data):
        """Test Bollinger Bands tool computation."""
        from tools.quant.technical import bollinger
        result = bollinger.compute(sample_data)
        assert 'upper' in result.data
        assert 'mid' in result.data
        assert 'lower' in result.data

    def test_atr_tool(self, sample_data):
        """Test ATR tool computation."""
        from tools.quant.technical import atr
        result = atr.compute(sample_data)
        assert 'atr' in result.data


class TestPersonaStrategies:
    """Test personas/zettaranc/strategies/ layer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100)
        data = pd.DataFrame({
            'open': 100 + np.cumsum(np.random.randn(100) * 2),
            'high': 100 + np.cumsum(np.random.randn(100) * 2) + 3,
            'low': 100 + np.cumsum(np.random.randn(100) * 2) - 3,
            'close': 100 + np.cumsum(np.random.randn(100) * 2),
            'vol': np.random.randint(1000000, 10000000, 100),
        })
        data['high'] = data[['open', 'close', 'high']].max(axis=1) + 2
        data['low'] = data[['open', 'close', 'low']].min(axis=1) - 2
        return data

    def test_b1_strategy(self, sample_data):
        """Test B1 strategy."""
        from personas.zettaranc.strategies import B1Strategy
        strategy = B1Strategy()
        signal = strategy.detect(sample_data)
        assert signal.action in ['buy', 'hold', 'warning']
        assert 0.0 <= signal.confidence <= 1.0

    def test_b2_strategy(self, sample_data):
        """Test B2 break strategy."""
        from personas.zettaranc.strategies import B2BreakStrategy
        strategy = B2BreakStrategy()
        signal = strategy.detect(sample_data)
        assert signal.action in ['buy', 'hold', 'warning']
        assert 0.0 <= signal.confidence <= 1.0

    def test_five_score_strategy(self, sample_data):
        """Test Five Score strategy."""
        from personas.zettaranc.strategies import FiveScoreStrategy
        strategy = FiveScoreStrategy()
        result = strategy.score(sample_data)
        assert 0 <= result.score <= 5
        assert result.action in ['hold_firm', 'hold', 'halve', 'exit']

    def test_all_strategies_importable(self, sample_data):
        """Test that all strategies can be imported and run."""
        from personas.zettaranc.strategies import (
            B1Strategy, B2BreakStrategy, FiveScoreStrategy,
            SB1FakeFallStrategy, S1WarningStrategy, HalfReleaseStrategy,
            UltimateB1Strategy, SuperB1Strategy, SingleNeedle20Strategy,
            AbnormalMovementStrategy, PitTargetStrategy, ThreeWavesStrategy,
            TwoThirtyRuleStrategy, DoublePonytailStrategy, ThreeOutsideThreeStrategy,
            TopWindmillStrategy, ThreeQuartersVolumeStrategy, FakeBearishStrategy,
            DoubleGunStrategy, BuyExhaustionStrategy, LongShadowShortVolumeStrategy,
        )

        strategies = [
            SB1FakeFallStrategy(),
            S1WarningStrategy(),
            HalfReleaseStrategy(),
            UltimateB1Strategy(),
            SuperB1Strategy(),
            SingleNeedle20Strategy(),
            AbnormalMovementStrategy(),
            PitTargetStrategy(),
            ThreeWavesStrategy(),
            TwoThirtyRuleStrategy(),
            DoublePonytailStrategy(),
            ThreeOutsideThreeStrategy(),
            TopWindmillStrategy(),
            ThreeQuartersVolumeStrategy(),
            FakeBearishStrategy(),
            DoubleGunStrategy(),
            BuyExhaustionStrategy(),
            LongShadowShortVolumeStrategy(),
        ]

        for strategy in strategies:
            signal = strategy.detect(sample_data)
            assert signal.action in ['buy', 'sell', 'hold', 'warning', 'halve']
            assert 0.0 <= signal.confidence <= 1.0


class TestOrchestrationLayer:
    """Test orchestration/ layer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample OHLCV data for testing."""
        np.random.seed(42)
        dates = pd.date_range('2024-01-01', periods=100)
        data = pd.DataFrame({
            'open': 100 + np.cumsum(np.random.randn(100) * 2),
            'high': 100 + np.cumsum(np.random.randn(100) * 2) + 3,
            'low': 100 + np.cumsum(np.random.randn(100) * 2) - 3,
            'close': 100 + np.cumsum(np.random.randn(100) * 2),
            'vol': np.random.randint(1000000, 10000000, 100),
        })
        data['high'] = data[['open', 'close', 'high']].max(axis=1) + 2
        data['low'] = data[['open', 'close', 'low']].min(axis=1) - 2
        return data

    def test_router(self):
        """Test query routing."""
        from orchestration import Router

        router = Router()

        route = router.route('帮我看看B1信号', ['zettaranc'])
        assert route.primary == 'zettaranc'
        assert 'b1' in route.intent or 'analyze' == route.intent

    def test_tool_cache(self, sample_data):
        """Test tool caching."""
        from orchestration import ToolCache

        cache = ToolCache()
        df_hash = cache.hash_dataframe(sample_data)

        # Cache should be empty initially
        assert cache.get('kdj', df_hash) is None

        # Set a value
        test_result = {'test': 'data'}
        cache.set('kdj', df_hash, test_result)

        # Should be retrievable now
        assert cache.get('kdj', df_hash) == test_result

        # Stats
        stats = cache.stats()
        assert stats['entries'] == 1

    def test_signal_aggregator(self):
        """Test signal aggregation."""
        from orchestration import SignalAggregator
        from orchestration.signal_aggregator import PersonaSignal, ConflictStrategy

        aggregator = SignalAggregator(strategy=ConflictStrategy.CONFIDENCE_WEIGHTED)

        signals = [
            PersonaSignal('zettaranc', 'buy', 0.8, 'B1 confirmed', {}),
            PersonaSignal('zettaranc', 'hold', 0.6, 'Wait for more', {}),
        ]

        result = aggregator.aggregate(signals)
        assert result.action == 'buy'
        assert result.conflict_detected is True

    def test_engine_b1_query(self, sample_data):
        """Test orchestration engine with B1 query."""
        from orchestration import OrchestrationEngine
        from orchestration.engine import OrchestrationRequest

        engine = OrchestrationEngine()

        req = OrchestrationRequest(
            query='B1信号怎么看',
            df=sample_data,
            persona_priority=['zettaranc'],
        )

        resp = engine.execute(req)

        assert resp.route.primary == 'zettaranc'
        assert 'kdj' in resp.tool_results
        assert 'b1' in resp.strategy_results
        assert resp.aggregated_signal is not None

    def test_engine_five_score_query(self, sample_data):
        """Test orchestration engine with Five Score query."""
        from orchestration import OrchestrationEngine
        from orchestration.engine import OrchestrationRequest

        engine = OrchestrationEngine()

        req = OrchestrationRequest(
            query='帮我看看五点评分',
            df=sample_data,
        )

        resp = engine.execute(req)

        assert 'five_score' in resp.strategy_results
        assert resp.persona_analysis is not None

    def test_engine_multi_strategy_query(self, sample_data):
        """Test orchestration engine with multiple strategies."""
        from orchestration import OrchestrationEngine
        from orchestration.engine import OrchestrationRequest

        engine = OrchestrationEngine()

        req = OrchestrationRequest(
            query='B1和五点评分怎么看',
            df=sample_data,
        )

        resp = engine.execute(req)

        assert len(resp.strategy_results) >= 1
        assert resp.persona_analysis is not None
        assert len(resp.persona_analysis) > 0


class TestRealDataIntegration:
    """Integration tests with real market data (if Tushare token available)."""

    @pytest.fixture
    def real_data(self):
        """Fetch real data if Tushare token is available."""
        token = os.environ.get('TUSHARE_TOKEN')
        if not token:
            pytest.skip("TUSHARE_TOKEN not available")

        try:
            import tushare as ts
            ts.set_token(token)
            pro = ts.pro_api()
            pro._DataApi__http_url = "http://tsy.xiaodefa.cn"

            # Fetch 贵州茅台 data
            df = pro.daily(ts_code='600519.SH', start_date='20240101', end_date='20240601')
            df = df.sort_values('trade_date')
            df = df.rename(columns={
                'vol': 'vol',
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
            })
            return df
        except Exception as e:
            pytest.skip(f"Failed to fetch real data: {e}")

    def test_real_data_tools(self, real_data):
        """Test tools with real data."""
        from tools.quant.technical import kdj, bbi

        # KDJ
        result = kdj.compute(real_data)
        assert not result.data['J'].isna().all()

        # BBI
        result = bbi.compute(real_data)
        assert not result.data['bbi'].isna().all()

    def test_real_data_strategies(self, real_data):
        """Test strategies with real data."""
        from personas.zettaranc.strategies import B1Strategy, FiveScoreStrategy

        b1 = B1Strategy()
        signal = b1.detect(real_data)
        assert signal.action in ['buy', 'hold', 'warning']

        fs = FiveScoreStrategy()
        result = fs.score(real_data)
        assert 0 <= result.score <= 5

    def test_real_data_orchestration(self, real_data):
        """Test orchestration with real data."""
        from orchestration import OrchestrationEngine
        from orchestration.engine import OrchestrationRequest

        engine = OrchestrationEngine()

        req = OrchestrationRequest(
            query='帮我分析B1和五点',
            df=real_data,
        )

        resp = engine.execute(req)
        assert resp.route.primary == 'zettaranc'
        assert len(resp.tool_results) > 0
