"""
Local photograph loading for the landing page's referral-journey section.

The three licensed healthcare photographs in assets/images/ are base64-
embedded so they can be used inside custom HTML cards (fixed-height
object-fit crop, hover effects, accent labels) via
st.markdown(unsafe_allow_html=True) — the same pattern already used for
every other custom card in this app (see components/cards.py).
"""
from __future__ import annotations

import base64
from functools import lru_cache
from pathlib import Path

_IMAGES_DIR = Path(__file__).resolve().parent.parent / "assets" / "images"

_MIME_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


@lru_cache(maxsize=8)
def image_data_uri(filename: str) -> str:
    """Read an image from assets/images/ and return it as a data: URI."""
    path = _IMAGES_DIR / filename
    mime = _MIME_TYPES.get(path.suffix.lower(), "image/jpeg")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"
