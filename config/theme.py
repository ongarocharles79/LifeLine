"""
Centralized design tokens for LIFELINE's UI, and the mechanism that makes
custom-styled elements (KPI cards, panels, hero, pills, etc.) adapt to
Streamlit's active light/dark theme.

Streamlit's native widgets (buttons, inputs, sidebar, dataframes) already
re-theme themselves. This module exists only for the custom raw-HTML blocks
this app injects via st.markdown(unsafe_allow_html=True) in components/ and
pages/ — those need an explicit, theme-aware color source since they aren't
covered by Streamlit's own theming.

Theme detection uses st.context.theme.type (server-side, reflects both OS
prefers-color-scheme and a manual in-app override in Streamlit's settings
menu) rather than guessing via CSS alone.
"""
from __future__ import annotations

import streamlit as st

LIGHT_TOKENS: dict[str, str] = {
    "primary": "#2563EB",
    "primary-hover": "#1D4ED8",
    "secondary": "#0D9488",
    "success": "#059669",
    "warning": "#D97706",
    "error": "#DC2626",
    "info": "#0284C7",
    "text-primary": "#0F172A",
    "text-secondary": "#475569",
    "text-muted": "#64748B",
    "background": "#F8FAFC",
    "surface": "#FFFFFF",
    "surface-alt": "#F1F5F9",
    "border": "#E2E8F0",
}

DARK_TOKENS: dict[str, str] = {
    "primary": "#3B82F6",
    "primary-hover": "#60A5FA",
    "secondary": "#2DD4BF",
    "success": "#34D399",
    "warning": "#FBBF24",
    "error": "#F87171",
    "info": "#38BDF8",
    "text-primary": "#F1F5F9",
    "text-secondary": "#CBD5E1",
    "text-muted": "#94A3B8",
    "background": "#0F172A",
    "surface": "#1E293B",
    "surface-alt": "#334155",
    "border": "#334155",
}


def get_tokens(dark: bool) -> dict[str, str]:
    return DARK_TOKENS if dark else LIGHT_TOKENS


def is_dark_theme() -> bool:
    theme_type = st.context.theme.type if st.context.theme else None
    return (theme_type or "light") == "dark"


def inject_theme_vars() -> bool:
    """Emit :root CSS custom properties matching the active Streamlit theme.

    Returns True if dark mode is active, so callers (e.g. chart builders)
    can branch without re-reading st.context themselves.
    """
    dark = is_dark_theme()
    tokens = get_tokens(dark)
    declarations = "\n".join(f"  --{key}: {value};" for key, value in tokens.items())
    st.markdown(f"<style>\n:root {{\n{declarations}\n}}\n</style>", unsafe_allow_html=True)
    return dark
