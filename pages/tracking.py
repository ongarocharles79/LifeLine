"""
Live Tracking page: follow an active mission from dispatch through arrival.

Ambulance movement is a DEMO SIMULATION — each "Update Position" click
advances the ambulance a fixed step along the straight line between the
referring and receiving hospitals. This is not real GPS tracking.
"""
from __future__ import annotations

import streamlit as st

from components.cards import render_priority_badge, render_status_pill
from components.maps import render_mission_map
from config.settings import REFERRAL_STATUS_COLORS, SIMULATION_STEP_PERCENT
from database.connection import get_session
from database.models import ReferralStatus
from services import referral_service, tracking_service

_ACTIVE_STATUSES = [
    ReferralStatus.AMBULANCE_DISPATCHED,
    ReferralStatus.PATIENT_PICKED_UP,
    ReferralStatus.TRANSPORTING,
    ReferralStatus.ARRIVED,
]

# Matches the pickup/destination marker colors on the mission map — kept in
# sync by reusing the same status tokens rather than separate hardcoded hex.
_PICKUP_DOT_COLOR = REFERRAL_STATUS_COLORS["COMPLETED"]
_DESTINATION_DOT_COLOR = REFERRAL_STATUS_COLORS["ARRIVED"]


def _dot(color: str) -> str:
    return f'<span class="lifeline-status-dot" style="background:{color};"></span>'


def render() -> None:
    st.title(":material/location_on: Live Tracking")
    st.caption(
        f"Simulated ambulance movement — each Update Position click advances the ambulance "
        f"{SIMULATION_STEP_PERCENT:.0f}% of the trip along a straight line. Not real GPS."
    )

    with get_session() as session:
        active_referrals = [
            r for r in referral_service.list_referrals(session) if r.status in _ACTIVE_STATUSES
        ]

        if not active_referrals:
            st.info(
                "No active missions right now. Assign an ambulance to a referral on the "
                "Referrals → Assign Ambulance tab to start one."
            )
            return

        options = {
            r.id: f"{r.patient.full_name} — {r.referring_hospital.name} → {r.receiving_hospital.name} "
                  f"({r.status.value.replace('_', ' ').title()})"
            for r in active_referrals
        }
        referral_id = st.selectbox("Active mission", options=list(options.keys()), format_func=lambda rid: options[rid])
        referral = next(r for r in active_referrals if r.id == referral_id)
        mission = tracking_service.get_active_mission(session, referral.id)

        if mission is None:
            st.error("This referral has no associated mission record.")
            return

        ambulance = mission.ambulance
        is_emergency = referral.priority.value == "EMERGENCY"
        is_transporting = referral.status == ReferralStatus.TRANSPORTING

        if is_emergency:
            panel_class = "lifeline-panel lifeline-panel-emergency"
        elif is_transporting:
            panel_class = "lifeline-panel lifeline-panel-active"
        else:
            panel_class = "lifeline-panel"

        col_detail, col_map = st.columns([1, 1.4])

        with col_detail:
            st.markdown(f'<div class="{panel_class}">', unsafe_allow_html=True)

            st.markdown("##### Patient")
            st.markdown(
                f"**{referral.patient.full_name}** ({referral.patient.age or '?'}, {referral.patient.gender.value.title()}) "
                f"{render_priority_badge(referral.priority.value)}  \n"
                f"Condition: {referral.patient.condition or 'N/A'}",
                unsafe_allow_html=True,
            )

            st.markdown("##### Referral")
            st.markdown(
                f"{_dot(_PICKUP_DOT_COLOR)}Pickup: **{referral.referring_hospital.name}**  \n"
                f"{_dot(_DESTINATION_DOT_COLOR)}Destination: **{referral.receiving_hospital.name}**  \n"
                f"Status: {render_status_pill(referral.status.value, 'referral')}",
                unsafe_allow_html=True,
            )

            st.markdown("##### Ambulance")
            st.markdown(
                f"**{ambulance.plate_number}** ({ambulance.vehicle_type.value.replace('_', ' ').title()})  \n"
                f"Driver: {ambulance.driver_name}  \n"
                f"Fuel: {ambulance.fuel_level_percent:.0f}%  \n"
                f"Status: {render_status_pill(ambulance.status.value, 'ambulance')}",
                unsafe_allow_html=True,
            )

            st.markdown("##### Mission")
            st.markdown(
                f"Estimated distance: **{mission.distance_km:.1f} km** (straight-line estimate)  \n"
                f"Estimated total cost: **KES {mission.estimated_total_cost_kes:,.0f}**  \n"
                f"Progress: **{mission.progress_percent:.0f}%**  \n"
                f"Remaining: **{mission.distance_km * (1 - mission.progress_percent / 100):.1f} km**  \n"
                f"Started: {mission.started_at.strftime('%Y-%m-%d %H:%M')}"
            )

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br/>", unsafe_allow_html=True)
            _render_actions(session, referral, mission)

        with col_map:
            deck = render_mission_map(
                pickup_name=referral.referring_hospital.name,
                pickup_lat=mission.pickup_latitude, pickup_lon=mission.pickup_longitude,
                destination_name=referral.receiving_hospital.name,
                destination_lat=mission.destination_latitude, destination_lon=mission.destination_longitude,
                ambulance_lat=ambulance.current_latitude, ambulance_lon=ambulance.current_longitude,
                plate_number=ambulance.plate_number,
                is_emergency=is_emergency,
            )
            st.pydeck_chart(deck)
            st.progress(min(1.0, mission.progress_percent / 100))


def _render_actions(session, referral, mission) -> None:
    status = referral.status

    if status == ReferralStatus.AMBULANCE_DISPATCHED:
        if st.button("Mark Picked Up", type="primary", icon=":material/check:", width='stretch'):
            tracking_service.mark_picked_up(session, referral.id)
            session.commit()
            st.toast(f"{referral.patient.full_name} picked up.", icon=":material/check_circle:")
            st.rerun()

    elif status == ReferralStatus.PATIENT_PICKED_UP:
        if st.button("Start Transporting", type="primary", icon=":material/local_shipping:", width='stretch'):
            tracking_service.mark_transporting(session, referral.id)
            session.commit()
            st.toast("Mission started — now transporting.", icon=":material/local_shipping:")
            st.rerun()

    elif status == ReferralStatus.TRANSPORTING:
        if st.button("Update Position", type="primary", icon=":material/my_location:", width='stretch'):
            update = tracking_service.simulate_step(session, mission.id)
            session.commit()
            if update.progress_percent >= 100.0:
                st.toast(f"{referral.patient.full_name} has arrived at the destination.", icon=":material/location_on:")
            else:
                st.toast(f"Position updated — {update.progress_percent:.0f}% of the trip.", icon=":material/my_location:")
            st.rerun()
        st.caption(f"Advances the ambulance from {mission.progress_percent:.0f}% to "
                   f"{min(100.0, mission.progress_percent + SIMULATION_STEP_PERCENT):.0f}% of the trip.")

    elif status == ReferralStatus.ARRIVED:
        st.success("Ambulance has arrived at the destination. Complete the handover on the Patient Handover page.")
