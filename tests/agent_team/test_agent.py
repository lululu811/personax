# tests/agent_team/test_agent.py
import pytest
from unittest.mock import Mock, patch
import pandas as pd

from agent_team.core.agent import Agent
from agent_team.core.models import Thought, AgentContext


class TestAgent:
    @pytest.fixture
    def mock_persona_config(self):
        config = Mock()
        config.to_system_prompt.return_value = "你是Z哥"
        return config

    @pytest.mark.asyncio
    @patch("agent_team.core.agent.ResponseGenerator")
    async def test_think_returns_thought(self, mock_gen_cls, mock_persona_config):
        mock_gen = Mock()
        mock_gen.generate.return_value = "月线四块砖翻红，中期趋势转多。"
        mock_gen.llm_available = True
        mock_gen_cls.return_value = mock_gen

        agent = Agent(name="zettaranc", persona_config=mock_persona_config)
        ctx = AgentContext(tool_results={"kdj": Mock()})
        thought = await agent.think("帮我看看茅台", ctx)

        assert isinstance(thought, Thought)
        assert thought.agent_name == "zettaranc"
        assert "四块砖" in thought.content
        assert thought.confidence > 0

    @pytest.mark.asyncio
    @patch("agent_team.core.agent.ResponseGenerator")
    async def test_react_returns_rebuttal(self, mock_gen_cls, mock_persona_config):
        mock_gen = Mock()
        mock_gen.generate.return_value = "BOSS墨忽略了量能配合的问题。"
        mock_gen.llm_available = True
        mock_gen_cls.return_value = mock_gen

        agent = Agent(name="zettaranc", persona_config=mock_persona_config)
        others = [
            Thought(agent_name="boss_mo", content="1800是次高", key_points=["次高"]),
        ]
        thought = await agent.react("帮我看看茅台", others)

        assert isinstance(thought, Thought)
        assert thought.is_rebuttal is True
        assert thought.agent_name == "zettaranc"

    @pytest.mark.asyncio
    @patch("agent_team.core.agent.ResponseGenerator")
    async def test_think_with_llm_unavailable(self, mock_gen_cls, mock_persona_config):
        mock_gen = Mock()
        mock_gen.llm_available = False
        mock_gen.generate.return_value = "模板输出"
        mock_gen_cls.return_value = mock_gen

        agent = Agent(name="zettaranc", persona_config=mock_persona_config)
        ctx = AgentContext()
        thought = await agent.think("帮我看看茅台", ctx)

        assert isinstance(thought, Thought)
