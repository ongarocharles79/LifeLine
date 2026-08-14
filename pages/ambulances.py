"""
Ambulance Fleet page: browse the demo fleet and healthcare facilities on a
map, with status filters and a manual status override for dispatchers.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from components.cards import render_status_dot
from components.maps import render_overview_map
from components.tables import ambulances_table, render_dataframe
from database.connection import get_session
from database.models import Ambulance, AmbulanceStatus, Hospital
from services import ambulance_service


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


def _ambulances_df(ambulances: list[Ambulance]) -> pd.DataFrame:
    return pd.DataFrame([{
        "plate_number": a.plate_number,
        "driver_name": a.driver_name,
        "status": a.status.value,
        "fuel_level_percent": round(a.fuel_level_percent, 0),
        "current_latitude": a.current_latitude,
        "current_longitude": a.current_longitude,
    } for a in ambulances])


def render() -> None:
    st.title(":material/emergency: Ambulance Fleet & Facilities")
    st.caption("Demo fleet of 20+ ambulances and the Kisumu County facility network.")

    with get_session() as session:
        options = ["All"] + [s.value for s in AmbulanceStatus]
        requested = st.query_params.get("status")
        default_index = options.index(requested) if requested in options else 0

        status_filter = st.selectbox(
            "Filter fleet by status",
            options=options,
            index=default_index,
            format_func=lambda s: s if s == "All" else s.replace("_", " ").title(),
        )
        status = None if status_filter == "All" else AmbulanceStatus(status_filter)
        ambulances = ambulance_service.list_ambulances(session, status=status)

        st.subheader("Network Map")
        st.caption("Ambulance positions are simulated demo data, not live GPS.")
        all_ambulances = ambulance_service.list_ambulances(session)
        st.pydeck_chart(render_overview_map(_hospitals_df(session), _ambulances_df(all_ambulances)))

        legend_cols = st.columns(5)
        legend_statuses = ["AVAILABLE", "ON_TRANSFER", "ON_BREAK", "MAINTENANCE", "RETURNING"]
        for col, status_value in zip(legend_cols, legend_statuses):
            col.markdown(
                f"<div style='text-align:center;'>{render_status_dot(status_value, kind='ambulance')}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader(f"Fleet Roster ({len(ambulances)})")
        if not ambulances:
            st.info("No ambulances match this filter.")
        else:
            render_dataframe(ambulances_table(ambulances))

        st.markdown("<br/>", unsafe_allow_html=True)
        with st.expander("Manual status override (dispatcher tool)"):
            all_amb = ambulance_service.list_ambulances(session)
            labels = {a.id: f"{a.plate_number} — currently {a.status.value.replace('_', ' ').title()}" for a in all_amb}
            amb_id = st.selectbox("Ambulance", options=list(labels.keys()), format_func=lambda aid: labels[aid])
            new_status = st.selectbox("New status", options=[s.value for s in AmbulanceStatus],
                                       format_func=lambda s: s.replace("_", " ").title())
            if st.button("Update Status", icon=":material/sync:"):
                try:
                    ambulance_service.update_ambulance_status(session, amb_id, AmbulanceStatus(new_status))
                    session.commit()
                    st.toast("Ambulance status updated.", icon=":material/check_circle:")
                    st.rerun()
                except ValueError as exc:
                    st.error(str(exc))
