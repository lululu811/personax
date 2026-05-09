"""Startup environment configuration validation.

Non-blocking checks — prints warnings for missing optional configs,
logs critical errors for required configs. System has fallbacks for
most missing env vars, so this is advisory only.
"""

import os
import warnings
from dataclasses import dataclass, field
from typing import Callable

from shared.config import get_wiki_dirs, load_yaml


@dataclass
class EnvCheckResult:
    """Result of a single env check."""

    name: str
    status: str  # "ok" | "warning" | "error"
    message: str
    required: bool = False


class EnvChecker:
    """Validate environment configuration at startup.

    Usage:
        checker = EnvChecker()
        results = checker.check_all()
        checker.print_report(results)
    """

    def __init__(self):
        self._checks: list[Callable[[], EnvCheckResult]] = [
            self._check_llm_api,
            self._check_wiki_dirs,
            self._check_data_sources,
        ]

    # ------------------------------------------------------------------ #
    #  Public API
    # ------------------------------------------------------------------ #

    def check_all(self) -> list[EnvCheckResult]:
        """Run all env checks and return results."""
        return [check() for check in self._checks]

    def print_report(self, results: list[EnvCheckResult] | None = None) -> None:
        """Print a formatted report of env check results."""
        if results is None:
            results = self.check_all()

        warnings_list = [r for r in results if r.status == "warning"]
        errors_list = [r for r in results if r.status == "error"]
        ok_list = [r for r in results if r.status == "ok"]

        lines: list[str] = []
        lines.append("─" * 50)
        lines.append("  PersonaX 环境配置检查")
        lines.append("─" * 50)

        for r in ok_list:
            lines.append(f"  ✓ {r.name}: {r.message}")

        for r in warnings_list:
            lines.append(f"  ⚠ {r.name}: {r.message}")

        for r in errors_list:
            lines.append(f"  ✗ {r.name}: {r.message}")

        if not warnings_list and not errors_list:
            lines.append("  所有配置就绪 ✓")
        elif warnings_list and not errors_list:
            lines.append("")
            lines.append("  提示: 以上为可选配置，系统将以降级模式运行。")
        else:
            lines.append("")
            lines.append("  错误: 存在必需配置缺失，部分功能不可用。")

        lines.append("─" * 50)
        print("\n".join(lines))

    def validate(self) -> bool:
        """Run checks and return True if no errors (warnings are OK)."""
        results = self.check_all()
        self.print_report(results)
        return not any(r.status == "error" for r in results)

    # ------------------------------------------------------------------ #
    #  Individual checks
    # ------------------------------------------------------------------ #

    def _check_llm_api(self) -> EnvCheckResult:
        """Check LLM API key configuration."""
        provider = os.environ.get("LLM_PROVIDER", "dashscope").lower()
        env_vars = {
            "dashscope": ["DASHSCOPE_API_KEY", "LLM_API_KEY"],
            "openai": ["OPENAI_API_KEY", "LLM_API_KEY"],
            "anthropic": ["ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "LLM_API_KEY"],
            "kimi": ["ANTHROPIC_API_KEY", "LLM_API_KEY"],
            "minimax": ["ANTHROPIC_AUTH_TOKEN", "LLM_API_KEY"],
            "bailian": ["ANTHROPIC_AUTH_TOKEN", "LLM_API_KEY"],
        }
        keys_to_check = env_vars.get(provider, env_vars["dashscope"])
        has_key = any(os.environ.get(k) for k in keys_to_check)

        if has_key:
            return EnvCheckResult(
                name="LLM API",
                status="ok",
                message=f"{provider} API key 已配置",
            )
        return EnvCheckResult(
            name="LLM API",
            status="warning",
            message=f"未配置 {provider} API key（{', '.join(keys_to_check)}），"
                    "LLM 生成将回退到模板模式",
            required=False,
        )

    def _check_wiki_dirs(self) -> EnvCheckResult:
        """Check wiki knowledge base directories."""
        dirs = get_wiki_dirs()
        if dirs:
            return EnvCheckResult(
                name="Wiki 知识库",
                status="ok",
                message=f"已加载 {len(dirs)} 个 wiki 目录",
            )
        return EnvCheckResult(
            name="Wiki 知识库",
            status="warning",
            message="未找到 wiki 目录（检查 WIKI_PUBLIC_DIRS / WIKI_PERSONAL_DIRS "
                    "或 registry/wiki.yaml 配置）",
            required=False,
        )

    def _check_data_sources(self) -> EnvCheckResult:
        """Check enabled data source configurations."""
        try:
            sources = load_yaml("data_sources")["data_sources"]
        except Exception:
            return EnvCheckResult(
                name="数据源",
                status="warning",
                message="无法读取 registry/data_sources.yaml",
                required=False,
            )

        enabled_sources = [
            (name, cfg) for name, cfg in sources.items()
            if cfg.get("enabled", True)
        ]

        if not enabled_sources:
            return EnvCheckResult(
                name="数据源",
                status="ok",
                message="未启用任何数据源",
            )

        missing: list[str] = []
        for name, cfg in enabled_sources:
            token_env = cfg.get("config", {}).get("token_env")
            if token_env and not os.environ.get(token_env):
                missing.append(f"{name}({token_env})")

        if not missing:
            return EnvCheckResult(
                name="数据源",
                status="ok",
                message=f"{len(enabled_sources)} 个数据源已配置",
            )
        return EnvCheckResult(
            name="数据源",
            status="warning",
            message=f"以下数据源缺少 token: {', '.join(missing)}",
            required=False,
        )


# ------------------------------------------------------------------ #
#  Convenience functions
# ------------------------------------------------------------------ #

def check_env() -> bool:
    """Quick env check with printed report. Returns True if no errors."""
    return EnvChecker().validate()
