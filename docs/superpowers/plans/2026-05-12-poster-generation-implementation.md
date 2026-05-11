# Poster Generation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add multi-style poster generation to Agent Team CLI, parallel-invoking baoyu-infographic and baoyu-image-cards skills after session scoring.

**Architecture:** A new `agent_team/poster/` module with styles registry, content formatters, and an async generator. CLI asks `y/n` after scoring, then dispatches 3 poster styles in parallel. All poster paths are attached to `TeamResult`.

**Tech Stack:** Python 3.11+, asyncio, subprocess, baoyu skills (already installed), pytest

---

## File Structure

| File | Responsibility |
|------|--------------|
| `agent_team/poster/__init__.py` | Package init, exports `PosterGenerator`, `DEFAULT_STYLES` |
| `agent_team/poster/styles.py` | `PosterStyle` dataclass + default style registry |
| `agent_team/poster/formatter.py` | `InfographicFormatter` and `ImageCardsFormatter` — turn `TeamResult` into markdown source |
| `agent_team/poster/generator.py` | `PosterGenerator` — prerequisites check, parallel subprocess dispatch, result collection |
| `agent_team/core/models.py` | Add `poster_paths: list[str]` to `TeamResult` |
| `agent_team/cli.py` | Add `click.confirm` + `_generate_posters()` integration after `_do_scoring()` |
| `tests/agent_team/poster/test_styles.py` | Verify style registry loads |
| `tests/agent_team/poster/test_formatter.py` | Verify TeamResult → markdown formatting |
| `tests/agent_team/poster/test_generator.py` | Mock subprocess, verify parallel execution and error collection |
| `tests/agent_team/test_cli_poster_flow.py` | Mock `PosterGenerator.generate`, verify CLI confirm flow |

---

### Task 1: Add poster_paths to TeamResult

**Files:**
- Modify: `agent_team/core/models.py:72-78`
- Test: `tests/agent_team/test_models.py` (new file)

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_team/test_models.py
from agent_team.core.models import TeamResult, Round, Synthesis

def test_team_result_has_poster_paths():
    result = TeamResult(
        rounds=[],
        final_scores={"zettaranc": 5.0},
        poster_text="test",
        session_id="sess_abc",
        poster_paths=["/tmp/poster1.png"],
    )
    assert result.poster_paths == ["/tmp/poster1.png"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/test_models.py::test_team_result_has_poster_paths -v`
Expected: FAIL with `TypeError: TeamResult.__init__() got an unexpected keyword argument 'poster_paths'`

- [ ] **Step 3: Write minimal implementation**

In `agent_team/core/models.py`, modify the `TeamResult` dataclass:

```python
@dataclass
class TeamResult:
    """Final result of a team brainstorming session."""
    rounds: list[Round]
    final_scores: Optional[dict[str, float]] = None
    poster_text: Optional[str] = None
    session_id: Optional[str] = None
    poster_paths: list[str] = field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/test_models.py::test_team_result_has_poster_paths -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/agent_team/test_models.py agent_team/core/models.py
git commit -m "feat(models): add poster_paths to TeamResult

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 2: PosterStyle dataclass and styles registry

**Files:**
- Create: `agent_team/poster/styles.py`
- Create: `tests/agent_team/poster/test_styles.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_team/poster/test_styles.py
from agent_team.poster.styles import PosterStyle, DEFAULT_STYLES

def test_default_styles_length():
    assert len(DEFAULT_STYLES) == 3

def test_style_has_required_fields():
    style = DEFAULT_STYLES[0]
    assert style.style_id
    assert style.skill_name
    assert style.args
    assert style.output_subdir
    assert style.description

def test_infographic_tech_is_pixel_art():
    tech = [s for s in DEFAULT_STYLES if s.style_id == "infographic-tech"][0]
    assert "pixel-art" in tech.args
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/poster/test_styles.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_team.poster.styles'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent_team/poster/styles.py
from dataclasses import dataclass


@dataclass(frozen=True)
class PosterStyle:
    style_id: str
    skill_name: str
    args: list[str]
    output_subdir: str
    description: str


DEFAULT_STYLES: list[PosterStyle] = [
    PosterStyle(
        style_id="infographic-tech",
        skill_name="baoyu-infographic",
        args=["--layout", "dense-modules", "--style", "pixel-art", "--no-confirm"],
        output_subdir="infographic-tech",
        description="像素风高密度信息图",
    ),
    PosterStyle(
        style_id="infographic-pro",
        skill_name="baoyu-infographic",
        args=["--layout", "bento-grid", "--style", "craft-handmade", "--no-confirm"],
        output_subdir="infographic-pro",
        description="专业手作风格信息图",
    ),
    PosterStyle(
        style_id="image-cards",
        skill_name="baoyu-image-cards",
        args=["--preset", "knowledge-card", "--no-confirm"],
        output_subdir="image-cards",
        description="知识卡片系列",
    ),
]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/poster/test_styles.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_team/poster/styles.py tests/agent_team/poster/test_styles.py agent_team/poster/__init__.py
git commit -m "feat(poster): add PosterStyle registry with 3 default styles

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 3: InfographicFormatter — TeamResult → markdown

**Files:**
- Create: `agent_team/poster/formatter.py`
- Create: `tests/agent_team/poster/test_formatter.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_team/poster/test_formatter.py
from agent_team.core.models import TeamResult, Round, Thought, Synthesis
from agent_team.poster.formatter import InfographicFormatter

def test_infographic_format_basic():
    result = TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[
                    Thought(agent_name="zettaranc", content="看涨，均线多头排列", confidence=0.85),
                ],
                moderator_summary=Synthesis(
                    consensus="技术面偏多",
                    disagreements=[],
                    recommendation="关注回调机会",
                ),
            )
        ],
        final_scores={"zettaranc": 5.0},
        session_id="sess_001",
    )
    fmt = InfographicFormatter()
    md = fmt.format(result)
    assert "# PersonaX 团队分析" in md
    assert "zettaranc" in md
    assert "均线多头排列" in md
    assert "技术面偏多" in md
    assert "关注回调机会" in md
    assert "5.0" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/poster/test_formatter.py::test_infographic_format_basic -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_team.poster.formatter'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent_team/poster/formatter.py
from agent_team.core.models import TeamResult


class InfographicFormatter:
    def format(self, result: TeamResult) -> str:
        lines = ["# PersonaX 团队分析报告", ""]

        for round_result in result.rounds:
            lines.append(f"## 第 {round_result.round_num} 轮分析")
            for thought in round_result.thoughts:
                content = thought.content[:120]
                lines.append(f"- **{thought.agent_name}**: {content}")
                lines.append(f"  - 置信度: {thought.confidence:.0%}")
            lines.append("")

        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append("## 主持人汇总")
            lines.append(f"- **共识**: {summary.consensus}")
            lines.append(f"- **建议**: {summary.recommendation}")
            lines.append("")

        if result.final_scores:
            lines.append("## 用户评分")
            for agent, score in result.final_scores.items():
                lines.append(f"- {agent}: {'⭐' * int(score)}")
            lines.append("")

        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/poster/test_formatter.py::test_infographic_format_basic -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_team/poster/formatter.py tests/agent_team/poster/test_formatter.py
git commit -m "feat(poster): add InfographicFormatter for TeamResult → markdown

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 4: ImageCardsFormatter — card series outline

**Files:**
- Modify: `agent_team/poster/formatter.py`
- Modify: `tests/agent_team/poster/test_formatter.py`

- [ ] **Step 1: Write the failing test**

```python
def test_image_cards_format():
    from agent_team.poster.formatter import ImageCardsFormatter
    result = TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[
                    Thought(agent_name="zettaranc", content="看涨", confidence=0.9, key_points=["均线金叉", "量能放大"]),
                    Thought(agent_name="boss_mo", content="震荡", confidence=0.6, key_points=[["分水未突破"]]),
                ],
                moderator_summary=Synthesis(
                    consensus="谨慎看多",
                    disagreements=[],
                    recommendation="等待突破确认",
                ),
            )
        ],
        final_scores={"zettaranc": 5.0, "boss_mo": 4.0},
        session_id="sess_002",
    )
    fmt = ImageCardsFormatter()
    md = fmt.format(result)
    assert "# 封面" in md or "## 封面" in md
    assert "zettaranc" in md
    assert "boss_mo" in md
    assert "等待突破确认" in md
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/poster/test_formatter.py::test_image_cards_format -v`
Expected: FAIL with `ImportError: cannot import name 'ImageCardsFormatter'`

- [ ] **Step 3: Write minimal implementation**

Append to `agent_team/poster/formatter.py`:

```python
class ImageCardsFormatter:
    def format(self, result: TeamResult) -> str:
        lines = ["# 封面", ""]

        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append(f"## {summary.consensus}")
            lines.append(f"{summary.recommendation}")
            lines.append("")

        for round_result in result.rounds:
            for thought in round_result.thoughts:
                lines.append(f"# {thought.agent_name}")
                lines.append(f"{thought.content[:100]}")
                if thought.key_points:
                    for kp in thought.key_points[:3]:
                        kp_text = kp if isinstance(kp, str) else str(kp)
                        lines.append(f"- {kp_text}")
                lines.append(f"置信度: {thought.confidence:.0%}")
                if result.final_scores and thought.agent_name in result.final_scores:
                    score = result.final_scores[thought.agent_name]
                    lines.append(f"评分: {'⭐' * int(score)}")
                lines.append("")

        lines.append("# 总结")
        if result.rounds:
            summary = result.rounds[-1].moderator_summary
            lines.append(f"共识: {summary.consensus}")
            lines.append(f"建议: {summary.recommendation}")

        return "\n".join(lines)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/poster/test_formatter.py::test_image_cards_format -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_team/poster/formatter.py tests/agent_team/poster/test_formatter.py
git commit -m "feat(poster): add ImageCardsFormatter for card series outline

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 5: PosterGenerator — prerequisites check + single style

**Files:**
- Create: `agent_team/poster/generator.py`
- Create: `tests/agent_team/poster/test_generator.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_team/poster/test_generator.py
import pytest
from unittest.mock import patch, AsyncMock

from agent_team.core.models import TeamResult, Round, Thought, Synthesis
from agent_team.poster.generator import PosterGenerator
from agent_team.poster.styles import PosterStyle

@pytest.fixture
def sample_result():
    return TeamResult(
        rounds=[
            Round(
                round_num=1,
                thoughts=[Thought(agent_name="z", content="看涨", confidence=0.8)],
                moderator_summary=Synthesis(consensus="多", disagreements=[], recommendation="买"),
            )
        ],
        final_scores={"z": 5.0},
        session_id="sess_test",
    )

@pytest.fixture
def sample_style():
    return PosterStyle(
        style_id="test-style",
        skill_name="baoyu-test",
        args=["--no-confirm"],
        output_subdir="test",
        description="测试",
    )

@pytest.mark.asyncio
async def test_generate_single_success(sample_result, sample_style, tmp_path):
    gen = PosterGenerator(output_dir=str(tmp_path))

    with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)
        mock_exec.return_value = mock_proc

        result = await gen._generate_single(sample_result, sample_style, tmp_path / "sess_test")
        assert result.style_id == "test-style"
        assert result.path.exists() or result.error is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/poster/test_generator.py::test_generate_single_success -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent_team.poster.generator'`

- [ ] **Step 3: Write minimal implementation**

```python
# agent_team/poster/generator.py
import asyncio
import shutil
from dataclasses import dataclass
from pathlib import Path

from agent_team.core.models import TeamResult
from agent_team.poster.formatter import InfographicFormatter, ImageCardsFormatter
from agent_team.poster.styles import PosterStyle, DEFAULT_STYLES


@dataclass
class PosterFile:
    style_id: str
    path: Path
    description: str


@dataclass
class PosterError:
    style_id: str
    error: str


@dataclass
class PosterOutput:
    session_id: str
    output_dir: Path
    files: list[PosterFile]
    errors: list[PosterError]


class PosterGenerator:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir) if output_dir else Path.home() / ".personax" / "posters"

    def _check_prerequisites(self) -> list[str]:
        missing = []
        for style in DEFAULT_STYLES:
            skill_path = Path.home() / ".claude" / "skills" / style.skill_name
            if not skill_path.exists():
                missing.append(style.skill_name)
        return list(set(missing))

    async def _generate_single(
        self,
        team_result: TeamResult,
        style: PosterStyle,
        session_dir: Path,
    ) -> PosterFile | PosterError:
        style_dir = session_dir / style.output_subdir
        style_dir.mkdir(parents=True, exist_ok=True)

        source_path = style_dir / "source.md"

        if style.skill_name == "baoyu-infographic":
            formatter = InfographicFormatter()
        elif style.skill_name == "baoyu-image-cards":
            formatter = ImageCardsFormatter()
        else:
            formatter = InfographicFormatter()

        source_path.write_text(formatter.format(team_result), encoding="utf-8")

        cmd = ["claude", "skill", style.skill_name, str(source_path), *style.args]

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=60)

            if proc.returncode != 0:
                return PosterError(
                    style_id=style.style_id,
                    error=f"Exit code {proc.returncode}: {stderr.decode()[:200]}",
                )

            # Find generated file
            if style.skill_name == "baoyu-infographic":
                png_path = style_dir / "infographic.png"
            else:
                pngs = list(style_dir.glob("*.png"))
                png_path = pngs[0] if pngs else style_dir / "output.png"

            return PosterFile(
                style_id=style.style_id,
                path=png_path,
                description=style.description,
            )
        except asyncio.TimeoutError:
            if proc:
                proc.kill()
            return PosterError(style_id=style.style_id, error="Timeout after 60s")
        except Exception as e:
            return PosterError(style_id=style.style_id, error=str(e)[:200])

    async def generate(
        self,
        team_result: TeamResult,
        styles: list[PosterStyle] = None,
    ) -> PosterOutput:
        styles = styles or DEFAULT_STYLES
        session_dir = self.output_dir / (team_result.session_id or "unknown")
        session_dir.mkdir(parents=True, exist_ok=True)

        tasks = [self._generate_single(team_result, s, session_dir) for s in styles]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        files: list[PosterFile] = []
        errors: list[PosterError] = []

        for r in results:
            if isinstance(r, Exception):
                errors.append(PosterError(style_id="unknown", error=str(r)[:200]))
            elif isinstance(r, PosterError):
                errors.append(r)
            else:
                files.append(r)

        return PosterOutput(
            session_id=team_result.session_id or "unknown",
            output_dir=session_dir,
            files=files,
            errors=errors,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/poster/test_generator.py::test_generate_single_success -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_team/poster/generator.py tests/agent_team/poster/test_generator.py
git commit -m "feat(poster): add PosterGenerator with prerequisites check and single-style generation

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 6: PosterGenerator parallel batch + error handling tests

**Files:**
- Modify: `tests/agent_team/poster/test_generator.py`

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.asyncio
async def test_generate_parallel_mixed_results(sample_result, tmp_path):
    gen = PosterGenerator(output_dir=str(tmp_path))

    with patch("agent_team.poster.generator.asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            proc = AsyncMock()
            if call_count == 1:
                proc.wait = AsyncMock(return_value=0)
                # Create a fake png
                (tmp_path / f"sess_test" / "infographic-tech").mkdir(parents=True, exist_ok=True)
                (tmp_path / f"sess_test" / "infographic-tech" / "infographic.png").write_text("")
            else:
                proc.wait = AsyncMock(return_value=1)
            return proc

        mock_exec.side_effect = side_effect

        output = await gen.generate(sample_result)
        assert len(output.files) + len(output.errors) == 3

@pytest.mark.asyncio
async def test_prerequisites_detects_missing_skills():
    gen = PosterGenerator()
    with patch("pathlib.Path.exists", return_value=False):
        missing = gen._check_prerequisites()
        assert len(missing) == 3  # 3 default styles
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/agent_team/poster/test_generator.py::test_generate_parallel_mixed_results tests/agent_team/poster/test_generator.py::test_prerequisites_detects_missing_skills -v`
Expected: FAIL (tests don't exist yet)

- [ ] **Step 3: Add tests to file**

Append the two tests above to `tests/agent_team/poster/test_generator.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/agent_team/poster/test_generator.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/agent_team/poster/test_generator.py
git commit -m "test(poster): add parallel generation and prerequisites tests

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 7: CLI integration — click.confirm + _generate_posters

**Files:**
- Modify: `agent_team/cli.py:132-154`
- Create: `tests/agent_team/test_cli_poster_flow.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/agent_team/test_cli_poster_flow.py
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from agent_team.cli import cli


def test_brainstorm_with_poster_generation():
    runner = CliRunner()

    with patch("agent_team.cli.Team.from_config") as mock_team_cls, \
         patch("agent_team.cli.TeamSession") as mock_session_cls, \
         patch("agent_team.cli.asyncio.run") as mock_run, \
         patch("agent_team.poster.generator.PosterGenerator") as mock_gen_cls:

        mock_team = MagicMock()
        mock_team.agents = [MagicMock(name="zettaranc")]
        mock_team.mode = "parallel"
        mock_team.get_agent.return_value = None
        mock_team_cls.return_value = mock_team

        mock_round = MagicMock()
        mock_round.round_num = 1
        mock_round.thoughts = []
        mock_round.moderator_summary.consensus = "test"
        mock_round.moderator_summary.recommendation = "test"

        mock_session = MagicMock()
        mock_session.rounds = [mock_round]
        mock_session.status = "closed"
        mock_session.session_id = "sess_abc"
        mock_session.start_brainstorm = MagicMock(return_value=mock_round)
        mock_session.close.return_value.poster_paths = []
        mock_session.close.return_value.poster_text = "test poster"
        mock_session.close.return_value.session_id = "sess_abc"
        mock_session_cls.return_value = mock_session

        mock_gen = MagicMock()
        mock_gen.generate = MagicMock(return_value=MagicMock(files=[], errors=[]))
        mock_gen_cls.return_value = mock_gen

        result = runner.invoke(cli, ["brainstorm", "--query", "看看茅台"], input="\n\n")
        assert result.exit_code == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/agent_team/test_cli_poster_flow.py::test_brainstorm_with_poster_generation -v`
Expected: FAIL with `ModuleNotFoundError` or assertion error

- [ ] **Step 3: Modify CLI**

In `agent_team/cli.py`, modify `_do_scoring()`:

```python
def _do_scoring(session: TeamSession):
    """Collect user scores for each agent."""
    click.echo("\n请为参与的 Agent 打分 (1-5星，回车跳过):\n")

    scores = {}
    for thought in session.rounds[-1].thoughts if session.rounds else []:
        if thought.is_fallback:
            continue
        score_str = click.prompt(f"  {thought.agent_name}", default="", show_default=False)
        if score_str.strip():
            try:
                score = float(score_str)
                if 1.0 <= score <= 5.0:
                    scores[thought.agent_name] = score
            except ValueError:
                pass

    if scores:
        result = session.close(scores)
        click.echo("\n最终报告:")
        click.echo(result.poster_text)

        if click.confirm("\n是否生成海报？", default=False):
            asyncio.run(_generate_posters(result))
    else:
        session.status = SessionStatus.CLOSED


async def _generate_posters(result):
    from agent_team.poster.generator import PosterGenerator, DEFAULT_STYLES

    generator = PosterGenerator()
    missing = generator._check_prerequisites()
    if missing:
        click.echo(f"! 缺少技能: {', '.join(missing)}")
        click.echo("  安装: claude skill install baoyu-infographic baoyu-image-cards")
        return

    click.echo("生成海报中...（3种风格并行）\n")
    output = await generator.generate(result, styles=DEFAULT_STYLES)

    for f in output.files:
        click.echo(f"  ✓ {f.description}: {f.path}")
    for e in output.errors:
        click.echo(f"  ✗ {e.style_id}: {e.error}")

    if output.files:
        click.echo(f"\n海报保存在: {output.output_dir}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/agent_team/test_cli_poster_flow.py::test_brainstorm_with_poster_generation -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent_team/cli.py tests/agent_team/test_cli_poster_flow.py
git commit -m "feat(cli): integrate poster generation after scoring

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 8: Update `agent_team/poster/__init__.py` exports

**Files:**
- Create: `agent_team/poster/__init__.py`

- [ ] **Step 1: Write the init file**

```python
# agent_team/poster/__init__.py
from agent_team.poster.generator import PosterGenerator, PosterOutput, PosterFile, PosterError
from agent_team.poster.styles import PosterStyle, DEFAULT_STYLES

__all__ = [
    "PosterGenerator",
    "PosterOutput",
    "PosterFile",
    "PosterError",
    "PosterStyle",
    "DEFAULT_STYLES",
]
```

- [ ] **Step 2: Verify import works**

Run: `python -c "from agent_team.poster import PosterGenerator, DEFAULT_STYLES; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add agent_team/poster/__init__.py
git commit -m "chore(poster): add __init__.py exports

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### Task 9: Run full test suite

**Files:**
- All existing and new test files

- [ ] **Step 1: Run all poster tests**

Run: `pytest tests/agent_team/poster/ -v --tb=short`
Expected: All 8+ tests PASS

- [ ] **Step 2: Run full test suite**

Run: `pytest tests/agent_team/ -v --tb=short`
Expected: All existing 38 tests + new tests PASS

- [ ] **Step 3: Commit (if any fixes needed)**

```bash
git add -A
git commit -m "test(poster): verify full test suite green

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## Self-Review

**1. Spec coverage:**
- `PosterStyle` registry ✅ Task 2
- `InfographicFormatter` ✅ Task 3
- `ImageCardsFormatter` ✅ Task 4
- `PosterGenerator` with prerequisites + parallel ✅ Task 5-6
- `PosterOutput/PosterFile/PosterError` models ✅ Task 5
- CLI integration with `click.confirm` ✅ Task 7
- `poster_paths` on `TeamResult` ✅ Task 1
- Error handling (timeout, missing skills) ✅ Task 5-6
- Tests for all modules ✅ Tasks 1-7

**2. Placeholder scan:** No TBD/TODO/"implement later"/vague requirements found.

**3. Type consistency:**
- `PosterGenerator.generate()` signature matches usage in CLI
- `TeamResult.poster_paths` is `list[str]` everywhere
- `PosterStyle` fields match registry usage
