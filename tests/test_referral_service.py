import pytest

from database.models import Gender, PatientCondition, ReferralStatus
from services import ambulance_service, referral_service


def _make_referral(session, two_hospitals):
    referring, receiving = two_hospitals
    return referral_service.create_referral(
        session,
        patient_data=dict(full_name="Jane Doe", age=30, gender=Gender.FEMALE, condition="Test condition"),
        referring_hospital_id=referring.id,
        receiving_hospital_id=receiving.id,
        reason="Test referral reason",
    )


def test_create_referral_sets_estimate_and_status(session, two_hospitals):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    assert referral.status == ReferralStatus.REFERRED
    assert referral.estimated_distance_km > 0
    assert referral.estimated_cost_kes > 0


def test_create_referral_rejects_same_hospital(session, two_hospitals):
    referring, _ = two_hospitals
    with pytest.raises(ValueError):
        referral_service.create_referral(
            session,
            patient_data=dict(full_name="Jane Doe", age=30, gender=Gender.FEMALE),
            referring_hospital_id=referring.id,
            receiving_hospital_id=referring.id,
            reason="Invalid referral",
        )


def test_advance_referral_status_follows_legal_workflow(session, two_hospitals, available_ambulance):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    ambulance_service.auto_assign_ambulance(session, referral.id, assigned_by_user_id=None)
    session.commit()
    assert referral.status == ReferralStatus.AMBULANCE_DISPATCHED

    referral_service.advance_referral_status(session, referral.id, ReferralStatus.PATIENT_PICKED_UP)
    assert referral.status == ReferralStatus.PATIENT_PICKED_UP
    assert referral.picked_up_at is not None


def test_advance_referral_status_rejects_illegal_transition(session, two_hospitals):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    # REFERRED -> PATIENT_PICKED_UP is not a legal direct transition.
    with pytest.raises(ValueError):
        referral_service.advance_referral_status(session, referral.id, ReferralStatus.PATIENT_PICKED_UP)


def test_complete_handover_requires_arrived_status(session, two_hospitals):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    with pytest.raises(ValueError):
        referral_service.complete_handover(
            session, referral.id, vitals={}, interventions=None, medications_administered=None,
            notes=None, patient_condition=PatientCondition.STABLE, received_by_user_id=None,
        )


def test_complete_handover_frees_ambulance_and_completes_referral(session, two_hospitals, available_ambulance):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    mission = ambulance_service.auto_assign_ambulance(session, referral.id, assigned_by_user_id=None)
    session.commit()

    referral_service.advance_referral_status(session, referral.id, ReferralStatus.PATIENT_PICKED_UP)
    referral_service.advance_referral_status(session, referral.id, ReferralStatus.TRANSPORTING)
    referral_service.advance_referral_status(session, referral.id, ReferralStatus.ARRIVED)
    session.commit()

    referral_service.complete_handover(
        session, referral.id,
        vitals=dict(heart_rate_bpm=80, temperature_celsius=37.0),
        interventions="Oxygen", medications_administered="None",
        notes="Stable throughout", patient_condition=PatientCondition.STABLE,
        received_by_user_id=None,
    )
    session.commit()

    assert referral.status == ReferralStatus.COMPLETED
    assert mission.ambulance.status.value == "AVAILABLE"
