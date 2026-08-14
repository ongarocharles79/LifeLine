"""
Dashboard page: KPIs, charts, and the facilities/fleet overview map.

All figures are computed live from the database via services/referral_service
and services/ambulance_service — nothing here is hardcoded.
"""
from __future__ import annotations

from datetime import datetime, timedelta

import pandas as pd
import streamlit as st

from components import icons
from components.cards import render_kpi_card, render_kpi_row
from components.charts import (
    cost_analytics_chart,
    hospital_activity_bar,
    referral_status_donut,
    referral_trend_chart,
)
from components.maps import render_overview_map
from config.settings import PRIVATE_TRANSPORT_COST_MULTIPLIER
from config.theme import is_dark_theme
from database.connection import get_session
from database.models import Ambulance, Hospital, Mission, Referral
from services import referral_service


def _referral_trend_df(session) -> pd.DataFrame:
    since = datetime.utcnow() - timedelta(days=30)
    referrals = session.query(Referral.created_at).filter(Referral.created_at >= since).all()
    dates = pd.Series([r.created_at.date() for r in referrals])
    date_range = pd.date_range(end=datetime.utcnow().date(), periods=30).date
    counts = dates.value_counts().reindex(date_range, fill_value=0).sort_index()
    return pd.DataFrame({"date": counts.index, "count": counts.values})


def _referral_status_df(session) -> pd.DataFrame:
    referrals = session.query(Referral.status).all()
    statuses = pd.Series([r.status.value for r in referrals])
    counts = statuses.value_counts()
    return pd.DataFrame({"status": counts.index, "count": counts.values})


def _cost_analytics_df(session) -> pd.DataFrame:
    since = datetime.utcnow() - timedelta(days=30)
    missions = (
        session.query(Mission.started_at, Mission.estimated_fuel_cost_kes, Mission.estimated_operating_cost_kes)
        .filter(Mission.started_at >= since)
        .all()
    )
    df = pd.DataFrame(missions, columns=["date", "fuel_cost", "operating_cost"])
    if df.empty:
        return pd.DataFrame({"date": [], "fuel_cost": [], "operating_cost": []})
    df["date"] = pd.to_datetime(df["date"]).dt.date
    grouped = df.groupby("date", as_index=False)[["fuel_cost", "operating_cost"]].sum()
    return grouped.sort_values("date")


def _hospital_activity_df(session) -> pd.DataFrame:
    hospitals = session.query(Hospital).all()
    counts = []
    for h in hospitals:
        count = (
            session.query(Referral)
            .filter((Referral.referring_hospital_id == h.id) | (Referral.receiving_hospital_id == h.id))
            .count()
        )
        if count > 0:
            counts.append({"hospital": h.name, "count": count})
    df = pd.DataFrame(counts).sort_values("count", ascending=False).head(10)
    return df


def _hospitals_df(session) -> pd.DataFrame:
    hospitals = session.query(Hospital).filter(Hospital.is_active.is_(True)).all()
    return pd.DataFrame([{
        "name": h.name,
        "latitude": h.latitude,
        "longitude": h.longitude,
        "facility_type": h.facility_type.value,
        "bed_capacity": h.bed_capacity or "N/A",
        "address": h.address or "",
    } for h in hospitals])


def _ambulances_df(session) -> pd.DataFrame:
    ambulances = session.query(Ambulance).all()
    return pd.DataFrame([{
        "plate_number": a.plate_number,
        "driver_name": a.driver_name,
        "status": a.status.value,
        "fuel_level_percent": round(a.fuel_level_percent, 0),
        "current_latitude": a.current_latitude,
        "current_longitude": a.current_longitude,
    } for a in ambulances])


def _go_to(page_key: str, **query_params: str) -> None:
    pages = st.session_state.get("_nav_pages", {})
    target = pages.get(page_key)
    if target is not None:
        st.switch_page(target, query_params=query_params or None)


def render() -> None:
    st.title(":material/dashboard: Dashboard")
    st.caption("Live operational overview — computed from the current demo database.")
    dark_mode = is_dark_theme()

    with get_session() as session:
        kpis = referral_service.compute_kpis(session)

        avg_response = f"{kpis.avg_response_time_minutes:.0f} min" if kpis.avg_response_time_minutes else "N/A"

        row1 = [
            dict(label="Total Referrals", value=str(kpis.total_referrals), icon_svg=icons.referrals()),
            dict(label="Active Referrals", value=str(kpis.active_referrals), icon_svg=icons.activity(), accent="primary"),
            dict(label="Available Ambulances", value=str(kpis.available_ambulances), icon_svg=icons.ambulance(), accent="success"),
            dict(label="Avg. Response Time", value=avg_response, icon_svg=icons.clock(),
                 help_text="Average time from when a referral is created to when an ambulance is dispatched, "
                            "averaged across every referral that has been dispatched."),
            dict(label="Completion Rate", value=f"{kpis.completion_rate_percent:.0f}%", icon_svg=icons.check_circle(), accent="success"),
        ]
        row1_actions = {
            1: ("View active referrals", "referrals", {"status": "ACTIVE"}),
            2: ("View fleet", "ambulances", {"status": "AVAILABLE"}),
            4: ("View completed", "referrals", {"status": "COMPLETED"}),
        }
        cols = st.columns(len(row1))
        for i, (col, kpi) in enumerate(zip(cols, row1)):
            with col:
                render_kpi_card(**kpi)
                if i in row1_actions:
                    label, page_key, params = row1_actions[i]
                    st.markdown('<div class="lifeline-kpi-action-row">', unsafe_allow_html=True)
                    # st.switch_page must be called from the main script body, not from
                    # inside an on_click callback (it does not navigate reliably there) —
                    # so this uses the same "if st.button(...):" pattern as the rest of
                    # the app rather than on_click.
                    if st.button(label, type="tertiary", icon=":material/arrow_forward:", key=f"kpi_action_{i}"):
                        _go_to(page_key, **params)
                    st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
        render_kpi_row([
            dict(label="Total Fuel Cost (KES)", value=f"{kpis.total_fuel_cost_kes:,.0f}", icon_svg=icons.fuel()),
            dict(label="Total Distance (km)", value=f"{kpis.total_distance_km:,.0f}", icon_svg=icons.route(),
                 help_text="Sum of the estimated straight-line (Haversine) distances recorded across every mission."),
            dict(label="Estimated Savings (KES)", value=f"{kpis.estimated_savings_kes:,.0f}", icon_svg=icons.savings(), accent="success",
                 help_text=f"Illustrative only: assumes private transport would cost "
                            f"{PRIVATE_TRANSPORT_COST_MULTIPLIER:.1f}× the fleet's actual trip cost. "
                            f"Savings = actual fleet cost × ({PRIVATE_TRANSPORT_COST_MULTIPLIER:.1f} − 1). "
                            f"Not a validated real-world benchmark."),
            dict(label="Fleet Efficiency", value=f"{kpis.fleet_efficiency_percent:.0f}%", icon_svg=icons.speed(),
                 help_text="Share of the fleet currently on an active transfer (ambulances with status "
                            "On Transfer, divided by total ambulances)."),
        ])

        st.markdown("<br/>", unsafe_allow_html=True)
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Referral Trends (30 Days)")
            st.plotly_chart(referral_trend_chart(_referral_trend_df(session), dark_mode), width='stretch')
        with col2:
            st.subheader("Referral Status")
            status_df = _referral_status_df(session)
            if status_df.empty:
                st.info("No referrals yet.")
            else:
                st.plotly_chart(referral_status_donut(status_df, dark_mode), width='stretch')

        col3, col4 = st.columns(2)
        with col3:
            st.subheader("Cost Analytics (30 Days)")
            cost_df = _cost_analytics_df(session)
            if cost_df.empty:
                st.info("No mission cost data in the last 30 days.")
            else:
                st.plotly_chart(cost_analytics_chart(cost_df, dark_mode), width='stretch')
        with col4:
            st.subheader("Hospital Activity")
            activity_df = _hospital_activity_df(session)
            if activity_df.empty:
                st.info("No hospital activity yet.")
            else:
                st.plotly_chart(hospital_activity_bar(activity_df, dark_mode), width='stretch')

        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Kisumu County Network Map")
        st.caption(
            "Facility coordinates are demo/seed data. Ambulance positions are simulated, not live GPS. "
            "Hover markers for details."
        )
        st.pydeck_chart(render_overview_map(_hospitals_df(session), _ambulances_df(session)))
