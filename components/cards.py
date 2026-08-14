"""
Reusable KPI/feature card, status-pill, and priority-badge renderers for
Streamlit pages.
"""
from __future__ import annotations

import streamlit as st

from components import icons
from config.settings import AMBULANCE_STATUS_COLORS, PRIORITY_COLORS, REFERRAL_STATUS_COLORS


def _tooltip_html(help_text: str) -> str:
    return (
        f'<span class="lifeline-tooltip-trigger" tabindex="0">{icons.info()}'
        f'<span class="lifeline-tooltip-bubble">{help_text}</span></span>'
    )


def render_kpi_card(
    label: str,
    value: str,
    delta: str | None = None,
    icon_svg: str = "",
    help_text: str | None = None,
    accent: str | None = None,
) -> None:
    """accent: one of "primary", "success", "warning", "error", or None."""
    delta_html = f'<div class="kpi-delta">{delta}</div>' if delta else ""
    value_class = f"kpi-value accent-{accent}" if accent else "kpi-value"
    label_html = f"{label}{_tooltip_html(help_text)}" if help_text else label
    st.markdown(
        f"""
        <div class="lifeline-kpi-card">
            <div class="kpi-icon">{icon_svg}</div>
            <div class="{value_class}">{value}</div>
            <div class="kpi-label">{label_html}</div>
            {delta_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(kpis: list[dict]) -> None:
    cols = st.columns(len(kpis))
    for col, kpi in zip(cols, kpis):
        with col:
            render_kpi_card(**kpi)


def render_feature_card(title: str, description: str, icon_svg: str) -> None:
    st.markdown(
        f"""
        <div class="lifeline-feature-card">
            <div class="feature-icon">{icon_svg}</div>
            <div class="feature-title">{title}</div>
            <div class="feature-description">{description}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_pill(status: str, kind: str = "referral") -> str:
    colors = REFERRAL_STATUS_COLORS if kind == "referral" else AMBULANCE_STATUS_COLORS
    color = colors.get(status, "#64748B")
    label = status.replace("_", " ").title()
    return (
        f'<span class="lifeline-status-pill" '
        f'style="background:{color}22;color:{color};border:1px solid {color}55;">{label}</span>'
    )


def render_status_dot(status: str, kind: str = "ambulance") -> str:
    """Small colored circle swatch for legends, e.g. the ambulance status key."""
    colors = REFERRAL_STATUS_COLORS if kind == "referral" else AMBULANCE_STATUS_COLORS
    color = colors.get(status, "#64748B")
    label = status.replace("_", " ").title()
    return (
        f'<span class="lifeline-legend-item">'
        f'<span class="lifeline-status-dot" style="background:{color};"></span>{label}</span>'
    )


def render_priority_badge(priority: str) -> str:
    """Referral priority badge. Red is used only here — the one place this
    app has real emergency/urgency data (ReferralPriority.EMERGENCY)."""
    color = PRIORITY_COLORS.get(priority, "#64748B")
    label = priority.title()
    return (
        f'<span class="lifeline-status-pill" '
        f'style="background:{color}22;color:{color};border:1px solid {color}55;">{label}</span>'
    )
