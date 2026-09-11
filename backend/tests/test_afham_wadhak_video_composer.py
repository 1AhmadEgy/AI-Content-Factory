from pathlib import Path

from app.services.video_composer import VideoComposer


ROOT = Path(__file__).resolve().parents[2]


def test_afham_wadhak_brand_profile_and_assets_exist():
    composer = VideoComposer("afham_wadhak")
    assert composer.config["name"] == "افهم واضحك"
    assert composer.config["canvas"] == {"width": 1080, "height": 1920, "fps": 30, "aspect_ratio": "9:16"}
    for relative in (
        "assets/branding/afham_wadhak/logo.svg",
        "assets/branding/afham_wadhak/logo_transparent.png",
        "assets/branding/afham_wadhak/avatar.png",
        "assets/branding/afham_wadhak/watermark.png",
        "assets/branding/afham_wadhak/thumbnail_template.png",
        "assets/branding/afham_wadhak/intro.mp4",
        "assets/branding/afham_wadhak/outro.mp4",
        "assets/branding/afham_wadhak/jingle.mp3",
    ):
        assert (ROOT / relative).exists(), relative
