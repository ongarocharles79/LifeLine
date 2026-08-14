"""
Inline SVG icon set for LIFELINE's custom-rendered UI (KPI cards, feature
cards, brand mark). Streamlit's own widgets (buttons, nav, alerts, titles)
use the built-in ":material/icon_name:" Material Symbols shortcode instead
(see app.py / pages/*.py) — this module exists only for the raw-HTML blocks
this app injects itself, where that shortcode substitution can't be relied
on to run inside unsafe_allow_html content.

Every icon uses stroke="currentColor" (or fill="currentColor" for the one
text-based glyph) so it automatically inherits whatever color the
surrounding element sets — that's what makes these icons theme-aware
without any icon-specific dark/light variants.
"""
from __future__ import annotations

_WRAPPER = (
    '<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" '
    'stroke-linecap="round" stroke-linejoin="round" class="lifeline-icon-svg">{inner}</svg>'
)


def _svg(inner: str, size: int = 20) -> str:
    return _WRAPPER.format(size=size, inner=inner)


def brand(size: int = 24) -> str:
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="8" x2="12" y2="16"/>'
        '<line x1="8" y1="12" x2="16" y2="12"/>',
        size,
    )


def referrals(size: int = 20) -> str:
    return _svg(
        '<rect x="5" y="4" width="14" height="17" rx="2"/>'
        '<rect x="9" y="2" width="6" height="4" rx="1"/>'
        '<line x1="8" y1="11" x2="16" y2="11"/>'
        '<line x1="8" y1="15" x2="16" y2="15"/>',
        size,
    )


def handover(size: int = 20) -> str:
    return _svg(
        '<rect x="5" y="4" width="14" height="17" rx="2"/>'
        '<rect x="9" y="2" width="6" height="4" rx="1"/>'
        '<polyline points="8.5 13 11 15.5 15.5 10.5"/>',
        size,
    )


def activity(size: int = 20) -> str:
    return _svg('<polyline points="3 12 8 12 10 6 14 18 16 12 21 12"/>', size)


def ambulance(size: int = 20) -> str:
    return _svg(
        '<rect x="1" y="9" width="14" height="7" rx="1.5"/>'
        '<rect x="15" y="11" width="6" height="5" rx="1"/>'
        '<circle cx="6" cy="18" r="1.8"/>'
        '<circle cx="17" cy="18" r="1.8"/>'
        '<line x1="8" y1="10.5" x2="8" y2="14.5"/>'
        '<line x1="6" y1="12.5" x2="10" y2="12.5"/>',
        size,
    )


def clock(size: int = 20) -> str:
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="7" x2="12" y2="12"/>'
        '<line x1="12" y1="12" x2="15.5" y2="14"/>',
        size,
    )


def check_circle(size: int = 20) -> str:
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<polyline points="7.5 12.5 10.5 15.5 16.5 9"/>',
        size,
    )


def fuel(size: int = 20) -> str:
    return _svg(
        '<rect x="5" y="4" width="10" height="17" rx="1.5"/>'
        '<line x1="5" y1="10" x2="15" y2="10"/>'
        '<circle cx="10" cy="15" r="2"/>'
        '<line x1="17" y1="8" x2="20" y2="5"/>',
        size,
    )


def route(size: int = 20) -> str:
    return _svg(
        '<circle cx="6" cy="6" r="2.2"/>'
        '<circle cx="18" cy="18" r="2.2"/>'
        '<line x1="8" y1="7.5" x2="16" y2="16.5" stroke-dasharray="2.5 2.5"/>',
        size,
    )


def savings(size: int = 20) -> str:
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<text x="12" y="16.3" text-anchor="middle" font-size="11" '
        'font-family="Arial, sans-serif" fill="currentColor" stroke="none">$</text>',
        size,
    )


def speed(size: int = 20) -> str:
    return _svg(
        '<path d="M4 15a8 8 0 1 1 16 0"/>'
        '<line x1="12" y1="15" x2="16" y2="10"/>'
        '<circle cx="12" cy="15" r="1.3" fill="currentColor" stroke="none"/>',
        size,
    )


def tracking(size: int = 20) -> str:
    return _svg(
        '<path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>'
        '<circle cx="12" cy="10" r="3"/>',
        size,
    )


def map_icon(size: int = 20) -> str:
    return _svg(
        '<polygon points="3 6 9 4 15 6 21 4 21 18 15 20 9 18 3 20"/>'
        '<line x1="9" y1="4" x2="9" y2="18"/>'
        '<line x1="15" y1="6" x2="15" y2="20"/>',
        size,
    )


def info(size: int = 14) -> str:
    return _svg(
        '<circle cx="12" cy="12" r="9"/>'
        '<line x1="12" y1="11" x2="12" y2="16.5"/>'
        '<circle cx="12" cy="7.5" r="0.75" fill="currentColor" stroke="none"/>',
        size,
    )


def chevron_right(size: int = 20) -> str:
    return _svg('<polyline points="9 6 15 12 9 18"/>', size)


def reports(size: int = 20) -> str:
    return _svg(
        '<rect x="4" y="12" width="4" height="9" rx="0.5"/>'
        '<rect x="10" y="7" width="4" height="14" rx="0.5"/>'
        '<rect x="16" y="3" width="4" height="18" rx="0.5"/>',
        size,
    )
