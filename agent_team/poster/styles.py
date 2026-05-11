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
