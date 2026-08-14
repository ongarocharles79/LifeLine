"""
Plotly chart builders for the LIFELINE dashboard.

Each function accepts a small pandas DataFrame (already aggregated by the
calling page) and a dark_mode flag (see config/theme.py::is_dark_theme,
read once by the calling page) and returns a go.Figure. Pages render
figures via st.plotly_chart(fig, width='stretch').
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from config.settings import REFERRAL_STATUS_COLORS
from config.theme import get_tokens


def _hex_to_rgba(hex_color: str, alpha: float) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r}, {g}, {b}, {alpha})"


def _layout(dark_mode: bool) -> dict:
    tokens = get_tokens(dark_mode)
    return dict(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=tokens["text-primary"]),
        margin=dict(l=10, r=10, t=30, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(color=tokens["text-secondary"])),
        hoverlabel=dict(
            bgcolor=tokens["surface"],
            bordercolor=tokens["border"],
            font=dict(family="Inter, -apple-system, Segoe UI, sans-serif", color=tokens["text-primary"], size=12),
        ),
    )


def referral_trend_chart(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """df columns: date, count — referrals created per day over the last 30 days."""
    tokens = get_tokens(dark_mode)
    primary = tokens["primary"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["count"],
        mode="lines+markers",
        line=dict(color=primary, width=3, shape="spline"),
        marker=dict(size=6, color=primary),
        fill="tozeroy",
        fillcolor=_hex_to_rgba(primary, 0.08),
        name="Referrals",
        hovertemplate="%{x|%b %d}<br><b>%{y} referral(s)</b><extra></extra>",
    ))
    fig.update_layout(**_layout(dark_mode), height=320, showlegend=False, hovermode="x unified")
    fig.update_xaxes(showgrid=False, color=tokens["text-secondary"])
    fig.update_yaxes(showgrid=True, gridcolor=tokens["border"], zeroline=False, rangemode="tozero", color=tokens["text-secondary"])
    return fig


def referral_status_donut(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """df columns: status, count."""
    tokens = get_tokens(dark_mode)
    colors = [REFERRAL_STATUS_COLORS.get(s, tokens["text-muted"]) for s in df["status"]]
    labels = [s.replace("_", " ").title() for s in df["status"]]
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=df["count"],
        hole=0.55,
        marker=dict(colors=colors, line=dict(color=tokens["surface"], width=2)),
        textinfo="percent",
        textfont=dict(size=12, color=tokens["text-primary"]),
        hovertemplate="<b>%{label}</b><br>%{value} referral(s) (%{percent})<extra></extra>",
    )])
    fig.update_layout(**_layout(dark_mode), height=320)
    return fig


def cost_analytics_chart(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """df columns: date, fuel_cost, operating_cost."""
    tokens = get_tokens(dark_mode)
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["date"], y=df["fuel_cost"], name="Fuel Cost (KES)", marker_color=tokens["primary"],
        hovertemplate="%{x|%b %d}<br>Fuel: <b>KES %{y:,.0f}</b><extra></extra>",
    ))
    fig.add_trace(go.Bar(
        x=df["date"], y=df["operating_cost"], name="Operating Cost (KES)", marker_color=tokens["info"],
        hovertemplate="%{x|%b %d}<br>Operating: <b>KES %{y:,.0f}</b><extra></extra>",
    ))
    fig.update_layout(**_layout(dark_mode), height=320, barmode="stack", hovermode="x unified")
    fig.update_xaxes(showgrid=False, color=tokens["text-secondary"])
    fig.update_yaxes(showgrid=True, gridcolor=tokens["border"], zeroline=False, color=tokens["text-secondary"])
    return fig


def hospital_activity_bar(df: pd.DataFrame, dark_mode: bool = False) -> go.Figure:
    """df columns: hospital, count — top facilities by referral volume."""
    tokens = get_tokens(dark_mode)
    df_sorted = df.sort_values("count", ascending=True)
    fig = go.Figure(go.Bar(
        x=df_sorted["count"],
        y=df_sorted["hospital"],
        orientation="h",
        marker_color=tokens["primary"],
        hovertemplate="<b>%{y}</b><br>%{x} referral(s)<extra></extra>",
    ))
    fig.update_layout(**_layout(dark_mode), height=max(320, 28 * len(df_sorted)))
    fig.update_xaxes(showgrid=True, gridcolor=tokens["border"], zeroline=False, color=tokens["text-secondary"])
    fig.update_yaxes(showgrid=False, color=tokens["text-secondary"])
    return fig
