from __future__ import annotations

"""Stable metadata for the reusable Egypt content library.

The catalog is descriptive only: it does not own user data and never mutates
characters, locations, series context, or episode history.
"""

EGYPT_LIBRARY_ID = "local-library-egypt"
EGYPT_LIBRARY_NAME = "Egypt"
EGYPT_LIBRARY_VERSION = 1

EGYPT_LIBRARY_CATEGORIES = (
    "characters",
    "locations",
    "series_templates",
    "relationships",
    "continuity",
    "story_facts",
    "running_gags",
    "open_threads",
    "props",
    "visual_rules",
    "audio_rules",
)

EGYPT_SERIES_TEMPLATE_IDS = (
    "comedy-series",
    "action-series",
    "drama-series",
    "mystery-series",
    "adventure-series",
    "family-series",
)


def egypt_library_metadata() -> dict[str, object]:
    """Return a stable, UI/API-friendly description of the Egypt library."""
    return {
        "id": EGYPT_LIBRARY_ID,
        "name": EGYPT_LIBRARY_NAME,
        "version": EGYPT_LIBRARY_VERSION,
        "country": "Egypt",
        "reusable": True,
        "nonDestructive": True,
        "categories": list(EGYPT_LIBRARY_CATEGORIES),
        "seriesTemplates": list(EGYPT_SERIES_TEMPLATE_IDS),
    }
