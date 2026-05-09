"""PersonaLoader - Runtime loader for persona configuration.

Loads and parses personality.md + overrides.yaml into a structured PersonaConfig.
This allows the Engine to access persona traits, expression DNA, and mental models
at runtime for LLM prompt construction.

Usage:
    from personas.persona_loader import load_persona
    config = load_persona("zettaranc")
    print(config.identity)
    print(config.expression_dna["catchphrases"])
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

_PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class PersonaConfig:
    """Structured persona configuration for runtime use."""

    name: str
    identity: str = ""                     # 身份卡原始文本
    expression_dna: dict = field(default_factory=dict)   # 表达DNA结构化数据
    mental_models: list[dict] = field(default_factory=list)  # 核心心智模型
    heuristics: dict[str, list[str]] = field(default_factory=dict)  # 决策启发式
    values: dict = field(default_factory=dict)           # 价值观与反模式
    boundaries: list[str] = field(default_factory=list)  # 诚实边界
    thresholds: dict[str, Any] = field(default_factory=dict)  # 关键数字速查
    timeline: str = ""                     # 人物时间线
    sources: str = ""                      # 调研来源
    overrides: dict = field(default_factory=dict)  # overrides.yaml 内容

    def to_system_prompt(self) -> str:
        """Generate system prompt for LLM from persona config."""
        lines = [
            f"你是 {self.name}。",
            "",
            "【身份】",
            self.identity,
            "",
            "【表达规则】",
        ]

        # Expression DNA rules
        dna = self.expression_dna
        if "sentence_pattern" in dna:
            lines.append(f"- 句式：{dna['sentence_pattern']}")
        if "catchphrases" in dna:
            lines.append(f"- 口头禅：{', '.join(dna['catchphrases'][:5])}")
        if "slang" in dna:
            lines.append(f"- 黑话：交易中使用 {', '.join(list(dna['slang'].keys())[:10])} 等术语")
        if "forbidden" in dna:
            lines.append(f"- 禁忌：绝不使用 {'、'.join(dna['forbidden'][:5])}")
        if "analogies" in dna:
            lines.append(f"- 类比：善用 {', '.join(list(dna['analogies'].keys())[:5])} 等类比")

        lines.extend([
            "",
            "【核心心智模型】",
        ])
        for model in self.mental_models[:3]:
            lines.append(f"- {model.get('title', '')}：{model.get('summary', '')}")

        lines.extend([
            "",
            "【价值观】",
        ])
        for pursuit in self.values.get("pursue", [])[:5]:
            lines.append(f"- 追求：{pursuit}")
        for reject in self.values.get("reject", [])[:5]:
            lines.append(f"- 拒绝：{reject}")

        lines.extend([
            "",
            "【纪律】",
        ])
        for category, rules in list(self.heuristics.items())[:3]:
            lines.append(f"- {category}：{', '.join(rules[:3])}")

        lines.extend([
            "",
            "你必须严格遵守以上身份和表达规则回答问题。用第一人称「我」，直接以该人物的身份和口吻回应。",
        ])

        return "\n".join(lines)

    def get_threshold(self, key: str, default: Any = None) -> Any:
        """Get a threshold value by key."""
        return self.thresholds.get(key, default)


def _read_markdown(path: Path) -> str:
    """Read a markdown file."""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _read_yaml(path: Path) -> dict:
    """Read a yaml file."""
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _extract_sections(text: str) -> dict[str, str]:
    """Extract ## sections from markdown text."""
    sections = {}
    # Match ## headers and their content until next ## or end
    pattern = r"^##\s+(.+?)\n(.*?)(?=\n##\s|\Z)"
    matches = re.finditer(pattern, text, re.MULTILINE | re.DOTALL)
    for match in matches:
        title = match.group(1).strip()
        content = match.group(2).strip()
        sections[title] = content
    return sections


def _parse_expression_dna(content: str) -> dict:
    """Parse expression DNA section into structured data."""
    dna = {}

    # Extract sentence patterns from the first table
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if "句式指纹" in line or "Sentence Pattern" in line:
            # Look for the table row with "平均句长"
            for j in range(i, min(i + 10, len(lines))):
                if "平均句长" in lines[j]:
                    parts = lines[j].split("|")
                    if len(parts) >= 4:
                        dna["sentence_pattern"] = parts[3].strip()
                    break
            break

    # Extract catchphrases from table
    catchphrases = []
    in_catchphrase_table = False
    for line in lines:
        if "高频口癖" in line or "高频词汇" in line:
            in_catchphrase_table = True
            continue
        if in_catchphrase_table and line.startswith("|") and "---" not in line and "词汇" not in line:
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if len(parts) >= 1 and parts[0] and not parts[0].startswith("["):
                # Extract the phrase without quotes
                phrase = parts[0].strip("`").strip("「").strip("」")
                if phrase and len(phrase) < 30:
                    catchphrases.append(phrase)
        elif in_catchphrase_table and line.startswith("##"):
            break
    dna["catchphrases"] = catchphrases[:20]

    # Extract slang terms from ### 黑话体系 section
    # Format: **动作类**：卤煮=落袋为安、拍掉=止损清仓...
    slang = {}
    in_slang = False
    for line in lines:
        if "### 黑话" in line:
            in_slang = True
            continue
        if in_slang and line.startswith("###") and "黑话" not in line:
            break
        if in_slang and line.startswith("**") and "**" in line[2:]:
            # Parse: **动作类**：卤煮=落袋为安、拍掉=止损清仓
            text = line.strip("*").strip()
            if "：" in text or ":" in text:
                sep = "：" if "：" in text else ":"
                items_text = text.split(sep, 1)[1].strip()
                # Split by 、（Chinese comma）or ,
                for item in re.split(r"[、,]", items_text):
                    item = item.strip()
                    if "=" in item:
                        term, meaning = item.split("=", 1)
                        slang[term.strip()] = meaning.strip()
    dna["slang"] = slang

    # Extract forbidden words
    forbidden = []
    in_forbidden = False
    for line in lines:
        if "禁忌词" in line or "禁忌" in line:
            in_forbidden = True
            continue
        if in_forbidden and line.startswith("##"):
            break
        if in_forbidden and line.startswith("- ") and "「" in line:
            # Extract quoted phrase
            match = re.search(r"「(.+?)」", line)
            if match:
                forbidden.append(match.group(1))
    dna["forbidden"] = forbidden[:15]

    # Extract analogies
    # Format: - **少妇 vs 少女** = 沉稳 vs 冲动的交易心态
    analogies = {}
    in_analogy = False
    for line in lines:
        if "类比方式" in line:
            in_analogy = True
            continue
        if in_analogy and line.startswith("##"):
            break
        if in_analogy and line.startswith("- ") and ("=" in line or "=" in line):
            # Extract: **title** = description
            text = line[2:].strip()
            match = re.search(r"\*\*(.+?)\*\*\s*[=＝]\s*(.+)", text)
            if match:
                analogies[match.group(1).strip()] = match.group(2).strip()
    dna["analogies"] = analogies

    return dna


def _parse_mental_models(content: str) -> list[dict]:
    """Parse mental models section."""
    models = []
    # Match ### 模型 N: title
    pattern = r"###\s+模型\s*\d+[:：]\s*(.+?)\n(.*?)(?=\n###\s+模型|\Z)"
    matches = re.finditer(pattern, content, re.DOTALL)
    for match in matches:
        title = match.group(1).strip()
        body = match.group(2).strip()
        # Extract the "一句话" summary
        summary = ""
        for line in body.split("\n"):
            if "一句话" in line or line.startswith("**一句话**"):
                summary = line.split("：", 1)[-1].strip()
                break
        models.append({
            "title": title,
            "summary": summary or body[:200],
            "full": body,
        })
    return models


def _parse_heuristics(content: str) -> dict[str, list[str]]:
    """Parse decision heuristics section into categorized rules."""
    heuristics = {}
    current_category = "general"

    lines = content.split("\n")
    for line in lines:
        # Match category headers like ### 短线纪律
        if line.startswith("### "):
            current_category = line.replace("### ", "").strip()
            heuristics[current_category] = []
            continue

        # Match numbered rules like 1. **text**
        match = re.match(r"^\d+\.\s+\*\*(.+?)\*\*", line.strip())
        if match:
            rule = match.group(1).strip()
            heuristics.setdefault(current_category, []).append(rule)

    return heuristics


def _parse_values(content: str) -> dict:
    """Parse values section.

    Format:
      **我追求的**：
      1. 活下来 > 一切
      2. ...

      **我拒绝的**：凭感觉买卖、追涨杀跌、亏损死扛...

      **内在张力**：
      - 分享欲 vs 低调务实...
    """
    values = {"pursue": [], "reject": [], "tensions": []}

    lines = content.split("\n")
    in_pursue = False
    in_reject = False
    in_tensions = False

    for line in lines:
        stripped = line.strip()

        if "我追求的" in stripped and "追求" in stripped:
            in_pursue = True
            in_reject = False
            in_tensions = False
            continue
        if "我拒绝的" in stripped and "拒绝" in stripped:
            in_pursue = False
            in_reject = True
            in_tensions = False
            # Parse inline reject list: **我拒绝的**：item1、item2...
            if "：" in stripped or ":" in stripped:
                sep = "：" if "：" in stripped else ":"
                items_text = stripped.split(sep, 1)[1].strip().rstrip("。")
                for item in re.split(r"[、,]", items_text):
                    item = item.strip()
                    if item:
                        values["reject"].append(item)
            continue
        if "内在张力" in stripped:
            in_pursue = False
            in_reject = False
            in_tensions = True
            continue

        if stripped.startswith("##"):
            break

        # Parse list items for pursue and tensions
        if stripped.startswith("1.") or stripped.startswith("- "):
            item = re.sub(r"^\d+\.\s+", "", stripped).strip()
            item = re.sub(r"^-\s+", "", item).strip()
            item = item.lstrip("*").rstrip("*").strip()

            if in_pursue and item:
                values["pursue"].append(item)
            elif in_tensions and item:
                values["tensions"].append(item)

    return values


def _parse_boundaries(content: str) -> list[str]:
    """Parse honesty boundaries section."""
    boundaries = []
    for line in content.split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            item = stripped[2:].strip()
            if item:
                boundaries.append(item)
    return boundaries


def _parse_thresholds(content: str) -> dict[str, Any]:
    """Parse trading thresholds from decision reference tables."""
    thresholds = {}

    # Extract key-value pairs from tables
    lines = content.split("\n")
    for line in lines:
        # Match | key | value | pattern
        if line.startswith("| ") and "---" not in line:
            parts = [p.strip() for p in line.split("|")]
            parts = [p for p in parts if p]
            if len(parts) == 2:
                key = parts[0].lower().replace(" ", "_").replace("/", "_")
                value = parts[1]
                # Try to parse as number
                try:
                    if "%" in value:
                        thresholds[key] = float(value.replace("%", "")) / 100
                    elif value.replace(".", "").replace("-", "").isdigit():
                        thresholds[key] = float(value)
                    else:
                        thresholds[key] = value
                except ValueError:
                    thresholds[key] = value

    return thresholds


def load_persona(persona_name: str) -> PersonaConfig:
    """Load persona configuration from personality.md and overrides.yaml.

    Args:
        persona_name: Name of the persona directory (e.g., "zettaranc")

    Returns:
        PersonaConfig with parsed identity, expression DNA, mental models, etc.
    """
    persona_dir = _PROJECT_ROOT / "personas" / persona_name

    if not persona_dir.exists():
        raise ValueError(f"Persona directory not found: {persona_dir}")

    # Read personality.md
    personality_path = persona_dir / "personality.md"
    if not personality_path.exists():
        raise ValueError(f"personality.md not found for persona: {persona_name}")

    personality_text = _read_markdown(personality_path)
    sections = _extract_sections(personality_text)

    # Read overrides.yaml
    overrides_path = persona_dir / "overrides.yaml"
    overrides = _read_yaml(overrides_path) if overrides_path.exists() else {}

    # Parse each section
    identity = sections.get("身份卡", "")
    expression_dna = _parse_expression_dna(sections.get("表达 DNA", ""))
    mental_models = _parse_mental_models(sections.get("核心心智模型", ""))
    heuristics = _parse_heuristics(sections.get("决策启发式", ""))
    values = _parse_values(sections.get("价值观与反模式", ""))
    boundaries = _parse_boundaries(sections.get("诚实边界", ""))
    thresholds = _parse_thresholds(sections.get("交易决策速查", ""))
    timeline = sections.get("人物时间线（关键节点）", "")
    sources = sections.get("调研来源", "")

    return PersonaConfig(
        name=persona_name,
        identity=identity,
        expression_dna=expression_dna,
        mental_models=mental_models,
        heuristics=heuristics,
        values=values,
        boundaries=boundaries,
        thresholds=thresholds,
        timeline=timeline,
        sources=sources,
        overrides=overrides,
    )


# Convenience function for quick access
def get_persona_config(persona_name: str) -> PersonaConfig:
    """Alias for load_persona."""
    return load_persona(persona_name)
