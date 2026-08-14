"""
Patient Handover page: capture clinical handover details for an arrived
patient, completing the referral and freeing the ambulance.
"""
from __future__ import annotations

import streamlit as st

from components.cards import render_priority_badge
from database.connection import get_session
from database.models import PatientCondition, ReferralStatus
from services import auth_service, referral_service


def render() -> None:
    st.title(":material/assignment_turned_in: Patient Handover")
    st.caption("Capture clinical handover details when a patient arrives at the receiving facility.")

    with get_session() as session:
        arrived = referral_service.list_referrals(session, status=ReferralStatus.ARRIVED)

        if not arrived:
            st.info("No patients are currently awaiting handover.")
            return

        options = {
            r.id: f"{r.patient.full_name} — arrived at {r.receiving_hospital.name}"
            for r in arrived
        }
        referral_id = st.selectbox("Arrived patient", options=list(options.keys()), format_func=lambda rid: options[rid])
        referral = next(r for r in arrived if r.id == referral_id)
        mission = referral.mission

        panel_class = "lifeline-panel lifeline-panel-emergency" if referral.priority.value == "EMERGENCY" else "lifeline-panel"
        st.markdown(
            f"""<div class="{panel_class}">
                <b>Patient:</b> {referral.patient.full_name} ({referral.patient.age or '?'}, {referral.patient.gender.value.title()})
                &nbsp; {render_priority_badge(referral.priority.value)}<br/>
                <b>Condition:</b> {referral.patient.condition or 'N/A'}<br/>
                <b>Referring hospital:</b> {referral.referring_hospital.name}<br/>
                <b>Receiving hospital:</b> {referral.receiving_hospital.name}<br/>
                <b>Ambulance:</b> {mission.ambulance.plate_number if mission else 'N/A'}<br/>
                <b>Distance:</b> {referral.estimated_distance_km:.1f} km (straight-line estimate)<br/>
                <b>Fuel cost:</b> KES {mission.estimated_fuel_cost_kes:,.0f} &nbsp;|&nbsp;
                <b>Total estimated cost:</b> KES {referral.estimated_cost_kes:,.0f}
            </div>""",
            unsafe_allow_html=True,
        )

        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("##### Vital Signs")
        v1, v2, v3 = st.columns(3)
        with v1:
            bp_sys = st.number_input("Blood pressure — systolic", min_value=0, max_value=300, value=120)
            hr = st.number_input("Heart rate (bpm)", min_value=0, max_value=300, value=80)
        with v2:
            bp_dia = st.number_input("Blood pressure — diastolic", min_value=0, max_value=200, value=80)
            temp = st.number_input("Temperature (°C)", min_value=25.0, max_value=45.0, value=37.0, step=0.1)
        with v3:
            spo2 = st.number_input("Oxygen saturation (SpO2 %)", min_value=0, max_value=100, value=97)
            resp_rate = st.number_input("Respiratory rate", min_value=0, max_value=80, value=18)
        glucose = st.number_input("Blood glucose (mmol/L)", min_value=0.0, max_value=40.0, value=5.5, step=0.1)

        st.markdown("##### Clinical Handover")
        interventions = st.text_area("Interventions performed en route")
        medications = st.text_area("Medications administered")
        notes = st.text_area("Handover notes")
        condition_on_arrival = st.selectbox(
            "Patient condition on arrival", options=[c.value for c in PatientCondition],
            format_func=lambda c: c.title(),
        )

        if st.button("Complete Handover", type="primary", icon=":material/task_alt:"):
            user = auth_service.current_user()
            try:
                referral_service.complete_handover(
                    session,
                    referral.id,
                    vitals=dict(
                        blood_pressure_systolic=int(bp_sys),
                        blood_pressure_diastolic=int(bp_dia),
                        heart_rate_bpm=int(hr),
                        temperature_celsius=float(temp),
                        spo2_percent=int(spo2),
                        respiratory_rate=int(resp_rate),
                        blood_glucose_mmol_l=float(glucose),
                    ),
                    interventions=interventions.strip() or None,
                    medications_administered=medications.strip() or None,
                    notes=notes.strip() or None,
                    patient_condition=PatientCondition(condition_on_arrival),
                    received_by_user_id=user["id"] if user else None,
                )
                session.commit()
                st.toast(
                    f"Handover complete for {referral.patient.full_name} — referral Completed, "
                    f"ambulance now Available.",
                    icon=":material/task_alt:",
                )
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))
