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
