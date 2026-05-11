import asyncio
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

        proc = None
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
