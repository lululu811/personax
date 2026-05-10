"""ResponseGenerator - LLM-powered persona-aware response generation.

Generates natural language responses in the persona's voice using:
1. PersonaConfig (identity, expression DNA, mental models)
2. Knowledge snippets from vector search
3. Quantitative data (tool results + strategy signals)

Supports multiple LLM backends:
- DashScope (Tongyi Qianwen)
- OpenAI-compatible APIs
- Anthropic Claude

Usage:
    from orchestration.response_generator import ResponseGenerator
    from personas.persona_loader import load_persona

    generator = ResponseGenerator()
    config = load_persona("zettaranc")

    analysis = generator.generate(
        query="帮我看看茅台的B1信号",
        persona_config=config,
        context={
            "knowledge_snippets": snippets,
            "tool_results": tool_results,
            "strategy_results": strategy_results,
            "aggregated_signal": aggregated,
        },
    )
"""

import os
from dataclasses import dataclass
from typing import Any, Optional

from personas.persona_loader import PersonaConfig


@dataclass
class GenerationContext:
    """Structured context for response generation."""
    knowledge_snippets: list[str] = None
    tool_results: dict = None
    strategy_results: dict = None
    aggregated_signal: Any = None
    stock_code: Optional[str] = None
    web_search_results: Optional[str] = None


class ResponseGenerator:
    """Generates persona-aware natural language responses.

    Supports multiple LLM backends via unified interface:
    - dashscope: Tongyi Qianwen (default)
    - openai: OpenAI-compatible APIs
    - minimax: MiniMax via Anthropic protocol
    - kimi: KIMI via Anthropic protocol
    - bailian: Bailian (百炼) via Anthropic protocol
    - anthropic: Standard Claude API

    Falls back to template mode when no API key is configured.
    """

    def __init__(
        self,
        provider: str = None,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
    ):
        # Provider selection: explicit > env > default
        self.provider = (provider or os.environ.get("LLM_PROVIDER", "dashscope")).lower()

        # Resolve credentials per provider
        if self.provider == "minimax":
            self.model = model or os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL", "MiniMax-M2.7-highspeed")
            self._api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("LLM_API_KEY")
            self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LLM_BASE_URL")
        elif self.provider == "kimi":
            self.model = model or os.environ.get("ANTHROPIC_DEFAULT_OPUS_MODEL") or os.environ.get("LLM_MODEL", "kimi-for-coding")
            self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("LLM_API_KEY")
            self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LLM_BASE_URL")
        elif self.provider == "bailian":
            self.model = model or os.environ.get("ANTHROPIC_DEFAULT_HAIKU_MODEL") or os.environ.get("LLM_MODEL", "qwen3.6-plus")
            self._api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("LLM_API_KEY")
            self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LLM_BASE_URL")
        elif self.provider == "anthropic":
            self.model = model or os.environ.get("ANTHROPIC_MODEL") or os.environ.get("LLM_MODEL", "claude-3-sonnet-20240229")
            self._api_key = api_key or os.environ.get("ANTHROPIC_AUTH_TOKEN") or os.environ.get("LLM_API_KEY")
            self._base_url = base_url or os.environ.get("ANTHROPIC_BASE_URL") or os.environ.get("LLM_BASE_URL")
        else:
            self.model = model or os.environ.get("LLM_MODEL", "qwen-plus")
            self._api_key = api_key or os.environ.get("LLM_API_KEY") or os.environ.get("DASHSCOPE_API_KEY")
            self._base_url = base_url or os.environ.get("LLM_BASE_URL")

        self._client = None
        self._init_client()

    def _init_client(self):
        """Initialize LLM client based on provider."""
        if not self._api_key:
            return

        if self.provider == "dashscope":
            try:
                import dashscope
                dashscope.api_key = self._api_key
                self._client = dashscope.Generation
            except ImportError:
                self._client = None

        elif self.provider in ("openai", "anthropic"):
            # Use openai client library for both OpenAI and Anthropic
            # Anthropic supports OpenAI-compatible API via base_url
            try:
                import openai as openai_lib
                client_kwargs = {"api_key": self._api_key}
                if self._base_url:
                    client_kwargs["base_url"] = self._base_url
                self._client = openai_lib.OpenAI(**client_kwargs)
            except ImportError:
                self._client = None

    @property
    def llm_available(self) -> bool:
        """Check if LLM generation is available."""
        if not self._api_key:
            return False
        # Anthropic-protocol providers use httpx directly, no pre-init client needed
        if self.provider in ("minimax", "anthropic", "kimi", "bailian"):
            return True
        return self._client is not None and self._api_key is not None

    # ------------------------------------------------------------------ #
    #  Main generation entrypoint
    # ------------------------------------------------------------------ #

    def generate(
        self,
        query: str,
        persona_config: PersonaConfig,
        context: GenerationContext | dict,
        history: list[dict] = None,
        attachments: list[Any] = None,
    ) -> str:
        """Generate a persona-aware response.

        Args:
            query: User's original query
            persona_config: Loaded persona configuration
            context: Quantitative context (tools, strategies, signals)
            history: Optional conversation history

        Returns:
            Natural language response in persona's voice
        """
        if isinstance(context, dict):
            context = GenerationContext(**context)

        if self.llm_available:
            return self._generate_llm(query, persona_config, context, history, attachments)
        else:
            return self._generate_template(query, persona_config, context)

    # ------------------------------------------------------------------ #
    #  Diagnosis workflow helpers
    # ------------------------------------------------------------------ #

    def generate_diagnosis_round1(
        self,
        query: str,
        route: Any,
        tool_results: dict,
        strategy_results: dict,
        questions: list[str],
        attachments: list[Any] = None,
    ) -> str:
        """Generate round-1 diagnosis questions with persona flavor."""
        if self.llm_available:
            system = self._build_diagnosis_system(route.primary if route else "zettaranc")
            context_parts = []

            if tool_results:
                context_parts.append("【技术指标】\n" + self._summarize_tools(tool_results))
            if strategy_results:
                context_parts.append("【策略信号】\n" + self._summarize_strategies(strategy_results))

            user_prompt = (
                f"用户问：{query}\n\n"
                f"请用你的人设口吻，自然地提出以下三个问题（不要列 1/2/3，用对话方式）：\n"
                + "\n".join(f"- {q}" for q in questions)
                + "\n\n要求：语气像聊天，短句为主，带设问。不要一次性全抛出去，像医生问诊一样层层深入。"
            )

            user_content = self._build_user_content(user_prompt, attachments)
            messages = [
                {"role": "system", "content": system + "\n\n" + "\n\n".join(context_parts)},
                {"role": "user", "content": user_content},
            ]
            return self._call_llm(messages)

        # Template fallback
        lines = [
            "这事儿我得先问你几个问题，不一样的。",
            "",
        ]
        for q in questions:
            lines.append(f"{q}")
        lines.append("")
        lines.append("(注：当前 LLM API 未配置，以上为结构化问诊。配置 API 后可获得人格化自然语言问诊。)")
        return "\n".join(lines)

    def generate_diagnosis_round2(
        self,
        query: str,
        state: Any,
        route_letter: Optional[str],
        route_label: str,
        questions: list[str],
        alert_msg: str = "",
        attachments: list[Any] = None,
    ) -> str:
        """Generate round-2 route-specific questions."""
        if self.llm_available:
            system = self._build_diagnosis_system(state.persona if state else "zettaranc")
            round1_answers = state.answers.get(1, {}) if state else {}

            context_parts = [f"【问诊阶段】{route_label}（路线 {route_letter}）"]
            if round1_answers:
                ans_text = ", ".join(f"{k}={v}" for k, v in round1_answers.items())
                context_parts.append(f"【第一轮回答】{ans_text}")
            if alert_msg:
                context_parts.append(f"【仓位警报】{alert_msg}")

            user_prompt = (
                f"用户回答：{query}\n\n"
                f"请继续用你的人设口吻，针对「{route_label}」提出以下问题：\n"
                + "\n".join(f"- {q}" for q in questions)
                + "\n\n要求：结合用户上一轮的回答，自然衔接。短句为主，带个人案例或反问。"
            )
            if alert_msg:
                user_prompt = f"⚠️ 先打断提醒仓位问题：{alert_msg}\n\n" + user_prompt

            user_content = self._build_user_content(user_prompt, attachments)
            messages = [
                {"role": "system", "content": system + "\n\n" + "\n\n".join(context_parts)},
                {"role": "user", "content": user_content},
            ]
            return self._call_llm(messages)

        # Template fallback
        lines = []
        if alert_msg:
            lines.append(f"⚠️ {alert_msg}")
            lines.append("")
        lines.append(f"好，进入「{route_label}」流程。")
        lines.append("")
        for q in questions:
            lines.append(f"{q}")
        lines.append("")
        lines.append("(注：当前 LLM API 未配置，以上为结构化问诊。)")
        return "\n".join(lines)

    def generate_diagnosis_conclusion(
        self,
        query: str,
        persona_config: PersonaConfig,
        state: Any,
        context: GenerationContext,
        diagnosis_helper: str,
        history: list[dict] = None,
        attachments: list[Any] = None,
    ) -> str:
        """Generate final diagnosis conclusion after round 2."""
        if isinstance(context, dict):
            context = GenerationContext(**context)

        round1 = state.answers.get(1, {}) if state else {}
        round2 = state.answers.get(2, {}) if state else {}
        route = state.diagnosis_route if state else "A"
        route_label = {"A": "持仓诊断", "B": "买点确认", "C": "逃命判断", "D": "长线配置"}.get(route, "诊断")

        if self.llm_available:
            system = persona_config.to_system_prompt()

            # Build rich context
            context_parts = [f"【问诊路线】{route_label}"]
            if round1:
                context_parts.append(f"【第一轮】{round1}")
            if round2:
                context_parts.append(f"【第二轮】{round2}")
            if diagnosis_helper:
                context_parts.append(f"【规则提示】{diagnosis_helper}")
            if context.knowledge_snippets:
                snippets_text = "\n\n".join(context.knowledge_snippets[:3])
                context_parts.append(f"【相关知识】\n{snippets_text}")
            if context.tool_results:
                tool_summary = self._summarize_tools(context.tool_results)
                if tool_summary:
                    context_parts.append(f"【技术指标】\n{tool_summary}")
            if context.strategy_results:
                strategy_summary = self._summarize_strategies(context.strategy_results)
                if strategy_summary:
                    context_parts.append(f"【策略信号】\n{strategy_summary}")
            if context.aggregated_signal:
                sig = context.aggregated_signal
                context_parts.append(f"【综合判断】{sig.action} (置信度: {sig.confidence:.0%})")

            system += "\n\n" + "\n\n".join(context_parts)

            user_prompt = (
                f"用户问：{query}\n\n"
                f"经过两轮问诊，请基于以上信息给出明确的诊断结论。\n"
                f"要求：\n"
                f"1. 直接回答可以买/不该买/先出来/再观察\n"
                f"2. 解释原因（用你的人设语气）\n"
                f"3. 如果信息不够，明确说还需要什么\n"
                f"4. 结尾用反问句或金句收尾"
            )

            user_content = self._build_user_content(user_prompt, attachments)
            messages = [{"role": "system", "content": system}]
            if history:
                for msg in history[-8:]:
                    messages.append(msg)
            messages.append({"role": "user", "content": user_content})

            return self._call_llm(messages)

        # Template fallback — use standard template but with diagnosis context
        lines = [
            f"【{route_label}结论】",
            "",
            diagnosis_helper,
            "",
        ]
        if context.tool_results:
            lines.append("【技术指标】")
            lines.append(self._summarize_tools(context.tool_results))
            lines.append("")
        if context.strategy_results:
            lines.append("【策略判断】")
            lines.append(self._summarize_strategies(context.strategy_results))
            lines.append("")
        if context.aggregated_signal:
            sig = context.aggregated_signal
            lines.append(f"【综合结论】{sig.action.upper()} (置信度 {sig.confidence:.0%})")
            if sig.reasons:
                lines.append(f"依据: {'; '.join(sig.reasons[:3])}")
        lines.append("")
        lines.append("(注：当前 LLM API 未配置，以上为结构化诊断。配置 API 后可获得人格化自然语言诊断。)")
        return "\n".join(lines)

    # ------------------------------------------------------------------ #
    #  LLM internals
    # ------------------------------------------------------------------ #

    def _generate_llm(
        self,
        query: str,
        persona_config: PersonaConfig,
        context: GenerationContext,
        history: list[dict] = None,
        attachments: list[Any] = None,
    ) -> str:
        """Generate response using LLM API."""
        messages = self._build_messages(query, persona_config, context, history, attachments)
        return self._call_llm(messages)

    def _call_llm(self, messages: list[dict]) -> str:
        """Call LLM API with unified interface."""
        try:
            if self.provider == "dashscope":
                return self._call_dashscope(messages)
            elif self.provider in ("minimax", "anthropic", "kimi", "bailian"):
                return self._call_anthropic(messages)
            elif self.provider == "openai":
                return self._call_openai(messages)
            else:
                raise ValueError(f"Unknown provider: {self.provider}")
        except Exception as e:
            # Return a graceful fallback indicating the error
            return f"[LLM 调用失败: {e}]\n\n{self._build_fallback_from_messages(messages)}"

    def _call_dashscope(self, messages: list[dict]) -> str:
        """Call DashScope (Tongyi Qianwen) API with multimodal support."""
        # Convert generic content blocks to DashScope/OpenAI-compatible format
        dashscope_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                ds_content = []
                for block in content:
                    if block.get("type") == "image":
                        mime = block.get("mime_type", "image/jpeg")
                        data = block.get("data", "")
                        ds_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        })
                    elif block.get("type") == "text":
                        ds_content.append({
                            "type": "text",
                            "text": block.get("text", ""),
                        })
                dashscope_messages.append({"role": msg["role"], "content": ds_content})
            else:
                dashscope_messages.append(msg)

        response = self._client.call(
            model=self.model,
            messages=dashscope_messages,
            result_format="message",
            max_tokens=1500,
            temperature=0.7,
        )
        if response.status_code == 200:
            return response.output.choices[0].message.content
        else:
            raise RuntimeError(f"DashScope API error: {response.status_code}")

    def _call_openai(self, messages: list[dict]) -> str:
        """Call OpenAI-compatible API with multimodal support."""
        # Convert generic content blocks to OpenAI format
        openai_messages = []
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, list):
                openai_content = []
                for block in content:
                    if block.get("type") == "image":
                        mime = block.get("mime_type", "image/jpeg")
                        data = block.get("data", "")
                        openai_content.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{data}"},
                        })
                    elif block.get("type") == "text":
                        openai_content.append({
                            "type": "text",
                            "text": block.get("text", ""),
                        })
                openai_messages.append({"role": msg["role"], "content": openai_content})
            else:
                openai_messages.append(msg)

        response = self._client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            max_tokens=1500,
            temperature=0.7,
        )
        return response.choices[0].message.content

    def _call_anthropic(self, messages: list[dict]) -> str:
        """Call native Anthropic Messages API using httpx."""
        import json
        try:
            import httpx
        except ImportError:
            raise ImportError("httpx is required for anthropic provider")

        # Extract system prompt and convert messages to Anthropic format
        system_prompt, anthropic_messages = self._convert_to_anthropic_messages(messages)

        url = f"{self._base_url.rstrip('/')}/v1/messages"
        headers = {
            "x-api-key": self._api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 1500,
            "messages": anthropic_messages,
        }
        if system_prompt:
            payload["system"] = system_prompt

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            # Find text block in content array (minimax returns thinking + text blocks)
            for block in data.get("content", []):
                if block.get("type") == "text":
                    return block["text"]
            # Fallback: try first content item
            content = data.get("content", [{}])[0]
            return content.get("text", str(content))

    def _convert_to_anthropic_messages(self, messages: list[dict]) -> tuple[Optional[str], list[dict]]:
        """Convert OpenAI-format messages to Anthropic format.

        Anthropic uses a separate 'system' parameter instead of system role messages.
        Returns: (system_prompt, anthropic_messages)
        """
        system_parts = []
        anthropic_messages = []

        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_parts.append(content)
            elif role in ("user", "assistant"):
                if isinstance(content, list):
                    anthropic_content = []
                    for block in content:
                        if block.get("type") == "image":
                            anthropic_content.append({
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": block.get("mime_type", "image/jpeg"),
                                    "data": block.get("data", ""),
                                },
                            })
                        elif block.get("type") == "text":
                            anthropic_content.append({
                                "type": "text",
                                "text": block.get("text", ""),
                            })
                    anthropic_messages.append({"role": role, "content": anthropic_content})
                else:
                    anthropic_messages.append({"role": role, "content": content})

        # If no user message at start, Anthropic requires alternating user/assistant
        # Ensure first message is from user
        if anthropic_messages and anthropic_messages[0]["role"] == "assistant":
            anthropic_messages.insert(0, {"role": "user", "content": "继续"})

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        return system_prompt, anthropic_messages

    def _build_messages(
        self,
        query: str,
        persona_config: PersonaConfig,
        context: GenerationContext,
        history: list[dict] = None,
        attachments: list[Any] = None,
    ) -> list[dict]:
        """Build messages for LLM API call.

        Supports multimodal input: if image attachments are provided,
        the user message content becomes a list of content blocks.
        """
        messages = []

        # System prompt: persona identity + expression rules
        system_content = persona_config.to_system_prompt()

        # Add quantitative context to system prompt
        context_parts = []

        if context.knowledge_snippets:
            snippets_text = "\n\n".join(context.knowledge_snippets[:3])
            context_parts.append(f"【相关知识】\n{snippets_text}")

        if context.tool_results:
            tool_summary = self._summarize_tools(context.tool_results)
            if tool_summary:
                context_parts.append(f"【技术指标】\n{tool_summary}")

        if context.strategy_results:
            strategy_summary = self._summarize_strategies(context.strategy_results)
            if strategy_summary:
                context_parts.append(f"【策略信号】\n{strategy_summary}")

        if context.web_search_results:
            context_parts.append(f"【实时信息】\n{context.web_search_results}")

        if context.aggregated_signal:
            sig = context.aggregated_signal
            context_parts.append(f"【综合判断】{sig.action} (置信度: {sig.confidence:.0%})")

        if context_parts:
            system_content += "\n\n" + "\n\n".join(context_parts)

        messages.append({"role": "system", "content": system_content})

        # Add conversation history if available
        if history:
            for msg in history[-6:]:
                messages.append(msg)

        # Build user message: text + optional image attachments
        user_content = self._build_user_content(query, attachments)
        messages.append({"role": "user", "content": user_content})

        return messages

    def _build_user_content(self, query: str, attachments: list[Any] | None) -> str | list[dict]:
        """Build user message content. Returns plain text or list of content blocks."""
        if not attachments:
            return query

        content_blocks = []
        for att in attachments:
            if hasattr(att, "is_image") and att.is_image():
                b64 = att.to_base64()
                if b64:
                    content_blocks.append({
                        "type": "image",
                        "mime_type": att.mime_type or "image/jpeg",
                        "data": b64,
                    })
        # Append text query last (convention: images first, then text)
        content_blocks.append({"type": "text", "text": query})
        return content_blocks

    def _build_diagnosis_system(self, persona_name: str) -> str:
        """Build a minimal system prompt for diagnosis rounds."""
        try:
            from personas.persona_loader import load_persona
            config = load_persona(persona_name)
            return config.to_system_prompt()
        except Exception:
            return (
                f"你是 {persona_name}。"
                "你是一位经验丰富的交易员，说话直率、爱用反问、短句为主。"
                "回答时要像聊天一样自然，不要像机器人列清单。"
            )

    def _build_fallback_from_messages(self, messages: list[dict]) -> str:
        """Build a readable fallback from messages when LLM fails."""
        lines = []
        for msg in messages:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if role == "user":
                lines.append(f"用户: {content}")
            elif role == "assistant":
                lines.append(f"回答: {content}")
        return "\n\n".join(lines) if lines else "LLM 调用失败，无法生成回复。"

    # ------------------------------------------------------------------ #
    #  Summarizers
    # ------------------------------------------------------------------ #

    def _summarize_tools(self, tool_results: dict) -> str:
        """Summarize tool results for LLM context."""
        lines = []
        for name, result in tool_results.items():
            if hasattr(result, "data") and result.data:
                last_values = {}
                for k, v in result.data.items():
                    if hasattr(v, "iloc"):
                        try:
                            last_values[k] = f"{v.iloc[-1]:.2f}"
                        except (TypeError, ValueError):
                            last_values[k] = str(v.iloc[-1])
                    else:
                        last_values[k] = str(v)
                lines.append(f"{name}: {last_values}")
            if hasattr(result, "signals") and result.signals:
                active = [k for k, v in result.signals.items() if v]
                if active:
                    lines.append(f"  信号: {', '.join(active)}")
        return "\n".join(lines)

    def _summarize_strategies(self, strategy_results: dict) -> str:
        """Summarize strategy results for LLM context.

        Includes metadata details (key price levels, phase progress, etc.)
        when available, so the LLM has rich quantitative context.
        """
        lines = []
        for name, signal in strategy_results.items():
            if signal.action != "hold":
                line = f"{name}: {signal.action} (置信度 {signal.confidence:.0%}) - {signal.reason}"
                # Append metadata details for richer context
                meta = getattr(signal, "metadata", None)
                if meta:
                    details = signal.metadata.get("details", {})
                    if details:
                        detail_str = self._format_details(details)
                        if detail_str:
                            line += f"\n  [{detail_str}]"
                lines.append(line)
        if not lines:
            lines.append("暂无明确策略信号")
        return "\n".join(lines)

    def _format_details(self, details: dict) -> str:
        """Format strategy metadata details for LLM context."""
        parts = []
        for key, val in details.items():
            if key in ("swings",):
                continue  # Skip raw complex structures
            if isinstance(val, dict):
                # e.g. {"price": 122.5, "type": "次高"}
                clean = {k: round(v, 2) if isinstance(v, float) else v for k, v in val.items()}
                parts.append(f"{key}={clean}")
            elif isinstance(val, float):
                parts.append(f"{key}={val:.2f}")
            elif isinstance(val, bool):
                pass  # Skip booleans for brevity
            else:
                parts.append(f"{key}={val}")
        return "; ".join(parts)

    # ------------------------------------------------------------------ #
    #  Template fallback (no LLM)
    # ------------------------------------------------------------------ #

    def _generate_template(
        self,
        query: str,
        persona_config: PersonaConfig,
        context: GenerationContext,
    ) -> str:
        """Generate response using template when LLM is unavailable.

        This produces a structured but persona-flavored response.
        """
        dna = persona_config.expression_dna
        lines = []

        # Opening with persona flavor
        catchphrases = dna.get("catchphrases", [])
        if catchphrases and "怎么看" in query:
            lines.append(f"这事儿，{catchphrases[0]}——")
        else:
            lines.append("这事我给你分析分析。")

        # Knowledge snippets
        if context.knowledge_snippets:
            lines.append("\n【相关背景】")
            for snippet in context.knowledge_snippets[:2]:
                # Extract content between brackets
                content = snippet.split("]\n", 1)[-1] if "]\n" in snippet else snippet
                lines.append(content[:200])

        # Tool results
        if context.tool_results:
            lines.append("\n【技术指标】")
            tool_summary = self._summarize_tools(context.tool_results)
            lines.append(tool_summary)

        # Strategy results
        if context.strategy_results:
            lines.append("\n【策略判断】")
            strategy_summary = self._summarize_strategies(context.strategy_results)
            lines.append(strategy_summary)

        # Aggregated signal
        if context.aggregated_signal:
            sig = context.aggregated_signal
            lines.append(f"\n【综合结论】{sig.action.upper()} (置信度 {sig.confidence:.0%})")
            if sig.reasons:
                lines.append(f"依据: {'; '.join(sig.reasons[:3])}")

        # Closing with persona style
        lines.append("\n---")
        lines.append("(注：当前 LLM API 未配置，以上为结构化分析。配置 LLM_API_KEY 后可获得人格化自然语言回答。)")

        return "\n".join(lines)
