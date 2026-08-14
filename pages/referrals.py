"""
Referrals page: browse all referrals, create a new referral (with a live
Haversine-based cost estimate), and assign an ambulance to a referral
awaiting dispatch.
"""
from __future__ import annotations

import streamlit as st

from components.cards import render_priority_badge
from components.tables import render_dataframe, referrals_table
from database.connection import get_session
from database.models import Gender, Hospital, ReferralPriority, ReferralStatus
from services import ambulance_service, auth_service, cost_service, referral_service


def _hospital_options(session) -> list[Hospital]:
    return session.query(Hospital).filter(Hospital.is_active.is_(True)).order_by(Hospital.name).all()


def render() -> None:
    st.title(":material/assignment: Referrals")
    st.caption("Create and manage patient referrals between healthcare facilities.")

    tab_all, tab_new, tab_assign = st.tabs(["All Referrals", "New Referral", "Assign Ambulance"])

    with tab_all:
        _render_all_referrals()

    with tab_new:
        _render_new_referral()

    with tab_assign:
        _render_assign_ambulance()


def _render_all_referrals() -> None:
    with get_session() as session:
        # "ALL"/"ACTIVE" are pseudo-options (not real ReferralStatus values);
        # kept upper-case like the real enum values so a query param such as
        # ?status=ACTIVE (used by the dashboard's clickable KPI cards) matches
        # directly without a case-mapping step.
        options = ["ALL", "ACTIVE"] + [s.value for s in ReferralStatus]
        requested = st.query_params.get("status")
        default_index = options.index(requested) if requested in options else 0

        status_filter = st.selectbox(
            "Filter by status",
            options=options,
            index=default_index,
            format_func=lambda s: s.replace("_", " ").title(),
        )

        if status_filter == "ALL":
            referrals = referral_service.list_referrals(session)
        elif status_filter == "ACTIVE":
            referrals = referral_service.get_active_referrals(session)
        else:
            referrals = referral_service.list_referrals(session, status=ReferralStatus(status_filter))

        if not referrals:
            st.info("No referrals match this filter yet.")
            return

        df = referrals_table(referrals)
        render_dataframe(df)
        st.caption(f"{len(referrals)} referral(s) shown.")


def _render_new_referral() -> None:
    with get_session() as session:
        hospitals = _hospital_options(session)
        hospital_names = {h.id: h.name for h in hospitals}

        st.markdown("##### Patient")
        p1, p2, p3 = st.columns(3)
        with p1:
            patient_name = st.text_input("Patient name", key="new_ref_patient_name")
        with p2:
            patient_age = st.number_input("Age", min_value=0, max_value=120, value=30, key="new_ref_age")
        with p3:
            patient_gender = st.selectbox("Gender", options=[g.value for g in Gender], key="new_ref_gender")
        condition = st.text_input("Condition", placeholder="e.g. Road traffic accident with suspected fracture", key="new_ref_condition")

        st.markdown("##### Referral")
        h1, h2 = st.columns(2)
        with h1:
            referring_id = st.selectbox(
                "Referring hospital", options=[h.id for h in hospitals],
                format_func=lambda hid: hospital_names[hid], key="new_ref_referring",
            )
        with h2:
            receiving_options = [h.id for h in hospitals if h.id != referring_id]
            receiving_id = st.selectbox(
                "Receiving hospital", options=receiving_options,
                format_func=lambda hid: hospital_names[hid], key="new_ref_receiving",
            )

        referring_hospital = next(h for h in hospitals if h.id == referring_id)
        receiving_hospital = next(h for h in hospitals if h.id == receiving_id)

        estimate = cost_service.estimate_referral_cost(
            referring_hospital.latitude, referring_hospital.longitude,
            receiving_hospital.latitude, receiving_hospital.longitude,
        )
        st.markdown(
            f"""<div class="lifeline-panel">
                <b>Estimated straight-line distance:</b> {estimate.distance_km:.1f} km (Haversine estimate, not road distance)<br/>
                <b>Estimated fuel:</b> {estimate.fuel_litres:.1f} L &nbsp; | &nbsp;
                <b>Estimated fuel cost:</b> KES {estimate.fuel_cost_kes:,.0f} &nbsp; | &nbsp;
                <b>Estimated operating cost:</b> KES {estimate.operating_cost_kes:,.0f}<br/>
                <b>Estimated total cost:</b> KES {estimate.total_cost_kes:,.0f}
            </div>""",
            unsafe_allow_html=True,
        )

        d1, d2 = st.columns(2)
        with d1:
            referring_physician = st.text_input("Referring physician", key="new_ref_ref_physician")
            priority = st.selectbox("Priority", options=[p.value for p in ReferralPriority], index=1, key="new_ref_priority")
            reason = st.text_area("Reason for referral", key="new_ref_reason")
            medical_history = st.text_area("Medical history", key="new_ref_history")
        with d2:
            receiving_physician = st.text_input("Receiving physician", key="new_ref_recv_physician")
            clinical_notes = st.text_area("Clinical notes", key="new_ref_notes")
            current_medications = st.text_area("Current medications", key="new_ref_meds")
            allergies = st.text_area("Allergies", key="new_ref_allergies")

        if st.button("Create Referral", type="primary", icon=":material/add:", key="new_ref_submit"):
            if not patient_name.strip():
                st.error("Patient name is required.")
                return
            if not reason.strip():
                st.error("Reason for referral is required.")
                return
            if referring_id == receiving_id:
                st.error("Referring and receiving hospital must be different.")
                return

            user = auth_service.current_user()
            try:
                referral = referral_service.create_referral(
                    session,
                    patient_data=dict(
                        full_name=patient_name.strip(),
                        age=int(patient_age),
                        gender=Gender(patient_gender),
                        condition=condition.strip() or None,
                    ),
                    referring_hospital_id=referring_id,
                    receiving_hospital_id=receiving_id,
                    reason=reason.strip(),
                    clinical_notes=clinical_notes.strip() or None,
                    medical_history=medical_history.strip() or None,
                    current_medications=current_medications.strip() or None,
                    allergies=allergies.strip() or None,
                    referring_physician=referring_physician.strip() or None,
                    receiving_physician=receiving_physician.strip() or None,
                    priority=ReferralPriority(priority),
                    referring_staff_id=user["id"] if user else None,
                )
                session.commit()
                st.success(
                    f"Referral created for {patient_name} — status **Referred**. "
                    f"Go to the Assign Ambulance tab to dispatch an ambulance."
                )
            except ValueError as exc:
                st.error(str(exc))


def _render_assign_ambulance() -> None:
    with get_session() as session:
        pending = referral_service.list_referrals(session, status=ReferralStatus.REFERRED)
        if not pending:
            st.info("No referrals are currently awaiting ambulance assignment.")
            return

        options = {r.id: f"{r.patient.full_name} — {r.referring_hospital.name} → {r.receiving_hospital.name}" for r in pending}
        referral_id = st.selectbox("Referral", options=list(options.keys()), format_func=lambda rid: options[rid])
        referral = next(r for r in pending if r.id == referral_id)

        panel_class = "lifeline-panel lifeline-panel-emergency" if referral.priority.value == "EMERGENCY" else "lifeline-panel"
        st.markdown(
            f"""<div class="{panel_class}">
                <b>Patient:</b> {referral.patient.full_name} ({referral.patient.age or '?'}, {referral.patient.gender.value.title()})
                &nbsp; {render_priority_badge(referral.priority.value)}<br/>
                <b>Condition:</b> {referral.patient.condition or 'N/A'}<br/>
                <b>Route:</b> {referral.referring_hospital.name} → {referral.receiving_hospital.name}<br/>
                <b>Estimated distance:</b> {referral.estimated_distance_km:.1f} km &nbsp;|&nbsp;
                <b>Estimated cost:</b> KES {referral.estimated_cost_kes:,.0f}
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        mode = st.radio("Assignment mode", ["Auto Assign (nearest available)", "Manual Assign"], horizontal=True)

        user = auth_service.current_user()

        if mode.startswith("Auto"):
            candidates = ambulance_service.find_nearest_available(
                session, referral.referring_hospital.latitude, referral.referring_hospital.longitude
            )
            if not candidates:
                st.warning("No available ambulance currently meets the assignment criteria (status/fuel).")
            else:
                best, distance_km = candidates[0]
                st.markdown(
                    f"**Best match:** {best.plate_number} · {best.driver_name} · "
                    f"{distance_km:.1f} km away · Fuel {best.fuel_level_percent:.0f}%"
                )
                if st.button("Auto Assign Ambulance", type="primary", icon=":material/bolt:", key="auto_assign_btn"):
                    try:
                        ambulance_service.auto_assign_ambulance(session, referral.id, user["id"] if user else None)
                        session.commit()
                        st.toast(f"Ambulance {best.plate_number} dispatched — status: Ambulance Dispatched.", icon=":material/check_circle:")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
        else:
            candidates = ambulance_service.find_nearest_available(
                session, referral.referring_hospital.latitude, referral.referring_hospital.longitude
            )
            if not candidates:
                st.warning("No available ambulances to choose from.")
            else:
                labels = {
                    amb.id: f"{amb.plate_number} · {amb.driver_name} · {dist:.1f} km · Fuel {amb.fuel_level_percent:.0f}%"
                    for amb, dist in candidates
                }
                chosen_id = st.selectbox("Select ambulance", options=list(labels.keys()), format_func=lambda aid: labels[aid])
                if st.button("Manual Assign Ambulance", type="primary", icon=":material/touch_app:", key="manual_assign_btn"):
                    try:
                        ambulance_service.manual_assign_ambulance(session, referral.id, chosen_id, user["id"] if user else None)
                        session.commit()
                        st.toast("Ambulance dispatched — status: Ambulance Dispatched.", icon=":material/check_circle:")
                        st.rerun()
                    except ValueError as exc:
                        st.error(str(exc))
