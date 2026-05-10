"""WebSearchTool 测试。

覆盖场景：
1. HTTPWebSearchProvider — 正常调用
2. HTTPWebSearchProvider — POST body + response_path
3. HTTPWebSearchProvider — 环境变量缺失时跳过 provider
4. HTTPWebSearchProvider — 多个 provider fallback
5. HTTPWebSearchProvider — API 异常处理
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock
from orchestration.web_search_tool import (
    SearchResult,
    HTTPWebSearchProvider,
    WebSearchTool,
)


class TestHTTPWebSearchProvider:
    """HTTPWebSearchProvider 测试。"""

    def test_parse_serper_format(self):
        """测试解析 Serper 格式响应 (organic 数组)。"""
        config = {
            "url": "https://google.serper.dev/search",
            "method": "POST",
            "headers": {"X-API-KEY": "test"},
            "body": {"q": "{query}"},
            "response_path": "organic",
        }
        provider = HTTPWebSearchProvider(config)

        data = {
            "organic": [
                {"title": "标题1", "snippet": "摘要1", "link": "https://a.com"},
                {"title": "标题2", "snippet": "摘要2", "link": "https://b.com"},
            ]
        }
        results = provider._parse_response(data, max_results=5)
        assert len(results) == 2
        assert results[0].title == "标题1"
        assert results[0].url == "https://a.com"

    def test_parse_serpapi_format(self):
        """测试解析 SerpApi 格式响应 (organic_results 数组)。"""
        config = {
            "url": "https://serpapi.com/search.json",
            "method": "GET",
            "params": {"q": "{query}"},
            "response_path": "organic_results",
        }
        provider = HTTPWebSearchProvider(config)

        data = {
            "organic_results": [
                {"title": "T1", "snippet": "S1", "link": "https://x.com"},
                {"title": "T2", "snippet": "S2", "link": "https://y.com"},
            ]
        }
        results = provider._parse_response(data, max_results=2)
        assert len(results) == 2
        assert results[0].title == "T1"

    def test_parse_nested_response_path(self):
        """测试解析嵌套路径 (如 webPages.value)。"""
        config = {
            "url": "https://api.bing.microsoft.com/v7.0/search",
            "response_path": "webPages.value",
        }
        provider = HTTPWebSearchProvider(config)

        data = {
            "webPages": {
                "value": [
                    {"title": "Bing1", "snippet": "Bs1", "url": "https://bing1.com"},
                    {"title": "Bing2", "snippet": "Bs2", "url": "https://bing2.com"},
                ]
            }
        }
        results = provider._parse_response(data, max_results=5)
        assert len(results) == 2
        assert results[0].title == "Bing1"

    def test_parse_flat_format(self):
        """测试解析扁平格式 (results/items/items)。"""
        config = {"url": "https://example.com/search"}
        provider = HTTPWebSearchProvider(config)

        data = {"results": [{"title": "R1", "snippet": "S1", "link": "https://r1.com"}]}
        results = provider._parse_response(data, max_results=5)
        assert len(results) == 1

    def test_max_results_limit(self):
        """测试 max_results 截断。"""
        config = {"url": "https://example.com/search"}
        provider = HTTPWebSearchProvider(config)

        data = {"organic": [{"title": f"T{i}", "snippet": f"S{i}", "link": f"https://t{i}.com"} for i in range(10)]}
        results = provider._parse_response(data, max_results=3)
        assert len(results) == 3

    def test_empty_response(self):
        """测试空响应。"""
        config = {"url": "https://example.com/search"}
        provider = HTTPWebSearchProvider(config)
        results = provider._parse_response({}, max_results=5)
        assert results == []


class TestEnvVarFallback:
    """环境变量缺失降级测试。"""

    def test_skip_provider_without_env(self):
        """未配置环境变量时跳过 provider。"""
        # 确保没有 MINIMAX_API_KEY
        old_val = os.environ.pop("MINIMAX_API_KEY", None)

        try:
            # 强制重新加载
            import orchestration.web_search_tool
            orchestration.web_search_tool._instance = None
            tool = WebSearchTool()
            assert "minimax" not in tool._providers
        finally:
            if old_val:
                os.environ["MINIMAX_API_KEY"] = old_val

    def test_load_provider_with_env(self):
        """配置环境变量后加载 provider。"""
        os.environ["MINIMAX_API_KEY"] = "test_key"

        try:
            import orchestration.web_search_tool
            orchestration.web_search_tool._instance = None
            tool = WebSearchTool()
            assert "minimax" in tool._providers
        finally:
            os.environ.pop("MINIMAX_API_KEY", None)


class TestMultiProviderFallback:
    """多 provider fallback 测试。"""

    def test_first_fails_second_succeeds(self):
        """第一个 provider 失败，第二个成功。"""
        import orchestration.web_search_tool
        orchestration.web_search_tool._instance = None

        tool = WebSearchTool()
        # 注入 mock provider
        fail_provider = MagicMock()
        fail_provider.search.side_effect = RuntimeError("API error")

        success_provider = MagicMock()
        success_provider.search.return_value = [
            SearchResult(title="OK", snippet="Success", url="https://ok.com")
        ]

        tool._providers = {"bad": fail_provider, "good": success_provider}

        result = tool.search("test query")
        assert "OK" in result
        assert "https://ok.com" in result

    def test_all_fail_returns_error(self):
        """所有 provider 失败返回错误信息。"""
        import orchestration.web_search_tool
        orchestration.web_search_tool._instance = None

        tool = WebSearchTool()
        fail_provider = MagicMock()
        fail_provider.search.side_effect = RuntimeError("down")
        tool._providers = {"bad": fail_provider}

        result = tool.search("test query")
        assert "WebSearch 失败" in result

    def test_no_providers_returns_empty(self):
        """没有 provider 返回空字符串。"""
        import orchestration.web_search_tool
        orchestration.web_search_tool._instance = None

        tool = WebSearchTool()
        tool._providers = {}

        result = tool.search("test query")
        assert result == ""


class TestFormatResults:
    """格式化结果测试。"""

    def test_format_single_result(self):
        """测试单条结果格式化。"""
        import orchestration.web_search_tool
        orchestration.web_search_tool._instance = None

        tool = WebSearchTool()
        results = [SearchResult(title="标题", snippet="摘要", url="https://x.com")]
        formatted = tool._format_results(results, "query")
        assert "【WebSearch: query】" in formatted
        assert "标题" in formatted
        assert "摘要" in formatted
        assert "https://x.com" in formatted

    def test_format_without_snippet(self):
        """测试没有摘要时格式化。"""
        import orchestration.web_search_tool
        orchestration.web_search_tool._instance = None

        tool = WebSearchTool()
        results = [SearchResult(title="标题", snippet="", url="https://x.com")]
        formatted = tool._format_results(results, "query")
        assert "标题" in formatted
        assert "https://x.com" in formatted
