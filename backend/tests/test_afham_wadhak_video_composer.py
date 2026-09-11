import json
from pathlib import Path

from app.services.video_composer import VideoComposer


ROOT = Path(__file__).resolve().parents[2]
BRAND_DIR = ROOT / "assets" / "branding" / "afham_wadhak"
CONFIG = ROOT / "backend" / "app" / "config" / "brands" / "afham_wadhak.json"


def test_afham_wadhak_brand_profile_matches_canonical_identity():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))

    assert config["brand_id"] == "afham_wadhak"
    assert config["brand_name_ar"] == "افهم واضحك"
    assert config["brand_name_en"] == "Afham Wadhak"
    assert config["tagline_ar"] == "افهم ببساطة وابتسم"
    assert config["color_palette"] == {
        "primary": "#111111",
        "secondary": "#FFD84D",
        "accent": "#4DB6FF",
        "text": "#FFFFFF",
        "neutral": "#2A2A2A",
        "background": "#111111",
    }
    assert config["watermark"]["opacity"] == 0.35
    assert config["watermark"]["position"] == "bottom_right"
    assert config["motion_identity"]["intro_duration_sec"] == 2.5
    assert config["motion_identity"]["outro_duration_sec"] == 2.5


def test_video_composer_loads_canonical_brand():
    composer = VideoComposer("afham_wadhak")
    assert composer.brand_id == "afham_wadhak"
    assert composer.config["brand_name_ar"] == "افهم واضحك"
    assert composer.config["brand_name_en"] == "Afham Wadhak"


def test_canonical_svg_sources_exist():
    for relative in (
        "logo.svg",
        "logo_transparent.svg",
        "icon.svg",
        "watermark.svg",
        "banner.svg",
        "thumbnail_template.svg",
    ):
        assert (BRAND_DIR / relative).exists(), relative
