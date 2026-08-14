"""
Reports page: referral / fleet / cost summaries with CSV export.
"""
from __future__ import annotations

import streamlit as st

from components.tables import referrals_table, render_dataframe, to_csv_bytes
from database.connection import get_session
from database.models import Ambulance, AmbulanceStatus, Mission
from services import referral_service


def render() -> None:
    st.title(":material/bar_chart: Reports")
    st.caption("Summary reports generated from the current demo database. Export to CSV for offline use.")

    with get_session() as session:
        kpis = referral_service.compute_kpis(session)
        all_ambulances = session.query(Ambulance).all()

        st.subheader("Referral Summary")
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total Referrals", kpis.total_referrals)
        completed = sum(1 for r in referral_service.list_referrals(session) if r.status.value == "COMPLETED")
        r2.metric("Completed Referrals", completed)
        r3.metric("Active Referrals", kpis.active_referrals)
        r4.metric(
            "Avg. Response Time",
            f"{kpis.avg_response_time_minutes:.0f} min" if kpis.avg_response_time_minutes else "N/A",
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Fleet Summary")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("Total Ambulances", len(all_ambulances))
        f2.metric("Available", sum(1 for a in all_ambulances if a.status == AmbulanceStatus.AVAILABLE))
        f3.metric("On Transfer", sum(1 for a in all_ambulances if a.status == AmbulanceStatus.ON_TRANSFER))
        f4.metric("Maintenance / Break", sum(
            1 for a in all_ambulances if a.status in (AmbulanceStatus.MAINTENANCE, AmbulanceStatus.ON_BREAK)
        ))

        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Cost Summary")
        c1, c2, c3 = st.columns(3)
        c1.metric("Total Fuel Cost (KES)", f"{kpis.total_fuel_cost_kes:,.0f}")
        c2.metric("Total Distance (km)", f"{kpis.total_distance_km:,.0f}")
        c3.metric("Estimated Savings (KES)", f"{kpis.estimated_savings_kes:,.0f}")
        st.caption(
            "Estimated savings is an illustrative heuristic comparing fleet operating cost against a "
            "private-transport baseline multiplier — not a validated real-world benchmark."
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        st.subheader("Referral Data Export")
        referrals = referral_service.list_referrals(session)
        df = referrals_table(referrals)
        render_dataframe(df)
        st.download_button(
            "Export Referrals to CSV",
            icon=":material/download:",
            data=to_csv_bytes(df),
            file_name="lifeline_referrals_export.csv",
            mime="text/csv",
        )
