"""WebSearch Provider 适配器。

从 registry/web_search.yaml 加载 provider 配置，
支持 HTTP 类型的搜索 provider。Engine 按列表顺序尝试，第一个失败自动 fallback。

未配置环境变量时自动跳过该 provider，优雅降级。

Usage:
    from orchestration.web_search_tool import WebSearchTool

    tool = WebSearchTool()
    results = tool.search("黄金 价格 今日", context="market_price")
    print(results)
"""

import os
import re
import httpx
from typing import Optional
from shared.config import load_yaml


class SearchResult:
    """A single web search result."""

    def __init__(self, title: str, snippet: str, url: str = ""):
        self.title = title
        self.snippet = snippet
        self.url = url

    def __repr__(self):
        return f"SearchResult(title={self.title!r}, snippet={self.snippet[:50]}...)"


class WebSearchProvider:
    """Base class for web search providers."""

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        raise NotImplementedError


class HTTPWebSearchProvider(WebSearchProvider):
    """HTTP-based web search provider."""

    def __init__(self, config: dict):
        self.url = config["url"]
        self.method = config.get("method", "GET")
        self.headers = config.get("headers", {})
        self.params_template = config.get("params", {})
        self.body_template = config.get("body", {})
        self.response_path = config.get("response_path", "")
        self.timeout = config.get("timeout", 10)

    def search(self, query: str, max_results: int = 5) -> list[SearchResult]:
        """Search via HTTP API (GET/POST)."""
        params = {}
        for k, v in self.params_template.items():
            if isinstance(v, str):
                params[k] = v.replace("{query}", query)
            else:
                params[k] = v

        headers = {}
        for k, v in self.headers.items():
            if isinstance(v, str) and "${" in v:
                headers[k] = re.sub(
                    r"\$\{([^}]+)\}",
                    lambda m: os.environ.get(m.group(1), ""),
                    v,
                )
            else:
                headers[k] = v

        body = None
        if self.body_template:
            body = {}
            for k, v in self.body_template.items():
                if isinstance(v, str):
                    body[k] = v.replace("{query}", query)
                else:
                    body[k] = v

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.request(
                method=self.method,
                url=self.url,
                params=params,
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            return self._parse_response(data, max_results)

    def _get_nested(self, data: dict, path: str):
        """Get a nested value from dict using dot-separated path."""
        if not path:
            return data
        keys = path.split(".")
        current = data
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key, [])
            elif isinstance(current, list):
                try:
                    current = current[int(key)]
                except (IndexError, ValueError):
                    return []
            else:
                return []
        return current if isinstance(current, list) else []

    def _parse_response(self, data: dict, max_results: int) -> list[SearchResult]:
        """Parse HTTP API response into SearchResult list."""
        items = self._get_nested(data, self.response_path)
        # If response_path returned the full dict, fall back to known keys
        if not isinstance(items, list):
            items = data.get("results", data.get("organic", data.get("items", [])))

        results = []
        for item in items[:max_results]:
            results.append(SearchResult(
                title=item.get("title", ""),
                snippet=item.get("snippet", item.get("description", item.get("summary", ""))),
                url=item.get("link", item.get("url", "")),
            ))
        return results


class WebSearchTool:
    """Unified web search interface for the orchestration engine.

    Loads providers from registry/web_search.yaml,
    tries them in order with automatic fallback.
    """

    def __init__(self):
        self._providers: dict[str, WebSearchProvider] = {}
        self._defaults = {}
        self._load_config()

    def _load_config(self):
        """Load provider config from registry/web_search.yaml."""
        config = load_yaml("web_search")
        providers_config = config.get("providers", {})
        self._defaults = config.get("defaults", {"max_results": 5, "timeout": 10})

        for name, pconfig in providers_config.items():
            ptype = pconfig.get("type", "")
            if ptype == "http":
                if not self._env_vars_available(pconfig):
                    continue
                self._providers[name] = HTTPWebSearchProvider(pconfig)

    @staticmethod
    def _env_vars_available(pconfig: dict) -> bool:
        """Check if all referenced env vars in config are set."""
        for section in (pconfig.get("headers", {}), pconfig.get("params", {})):
            for v in section.values():
                if isinstance(v, str):
                    for m in re.finditer(r"\$\{([^}]+)\}", v):
                        if not os.environ.get(m.group(1)):
                            return False
        return True

    def search(
        self,
        query: str,
        providers: Optional[list[str]] = None,
        context: str = "",
        max_results: Optional[int] = None,
    ) -> str:
        """Execute web search and return formatted text.

        Args:
            query: Search query
            providers: List of provider names to try (default: all)
            context: Search context hint (e.g., "macro", "market_price")
            max_results: Max results to return (default: from config)

        Returns:
            Formatted search results as text, or empty string if all failed
        """
        if max_results is None:
            max_results = self._defaults.get("max_results", 5)

        provider_names = providers or list(self._providers.keys())
        if not provider_names:
            return ""

        errors = []
        for name in provider_names:
            provider = self._providers.get(name)
            if not provider:
                continue

            try:
                # context is used as a hint for the provider, not appended to query
                results = provider.search(query, max_results)
                if results:
                    return self._format_results(results, query)
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue

        if errors:
            return f"[WebSearch 失败: {'; '.join(str(e) for e in errors)}]"
        return ""

    def _format_results(self, results: list[SearchResult], query: str) -> str:
        """Format search results as text for LLM context."""
        lines = [f"【WebSearch: {query}】"]
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.title}")
            if r.snippet:
                lines.append(f"   {r.snippet}")
            if r.url:
                lines.append(f"   {r.url}")
        return "\n".join(lines)

    def is_available(self, providers: Optional[list[str]] = None) -> bool:
        """Check if any usable web search provider is configured."""
        provider_names = providers or list(self._providers.keys())
        return any(name in self._providers for name in provider_names)


# Module-level singleton
_instance: Optional[WebSearchTool] = None


def get_web_search_tool() -> WebSearchTool:
    """Get the global WebSearchTool instance."""
    global _instance
    if _instance is None:
        _instance = WebSearchTool()
    return _instance
