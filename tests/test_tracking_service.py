import math

import pytest

from config.settings import SIMULATION_STEP_PERCENT
from database.models import Gender, ReferralStatus
from services import ambulance_service, referral_service, tracking_service


def _make_dispatched_mission(session, two_hospitals):
    referring, receiving = two_hospitals
    referral = referral_service.create_referral(
        session,
        patient_data=dict(full_name="Jane Doe", age=30, gender=Gender.FEMALE),
        referring_hospital_id=referring.id,
        receiving_hospital_id=receiving.id,
        reason="Test referral reason",
    )
    session.commit()
    mission = ambulance_service.auto_assign_ambulance(session, referral.id, assigned_by_user_id=None)
    session.commit()
    referral_service.advance_referral_status(session, referral.id, ReferralStatus.PATIENT_PICKED_UP)
    referral_service.advance_referral_status(session, referral.id, ReferralStatus.TRANSPORTING)
    session.commit()
    return referral, mission


def test_simulate_step_advances_progress_by_fixed_step(session, two_hospitals, available_ambulance):
    referral, mission = _make_dispatched_mission(session, two_hospitals)

    update = tracking_service.simulate_step(session, mission.id)

    assert math.isclose(mission.progress_percent, SIMULATION_STEP_PERCENT)
    assert math.isclose(update.progress_percent, SIMULATION_STEP_PERCENT)
    assert update.distance_remaining_km < mission.distance_km


def test_simulate_step_reaches_arrived_at_100_percent(session, two_hospitals, available_ambulance):
    referral, mission = _make_dispatched_mission(session, two_hospitals)

    steps_needed = math.ceil(100 / SIMULATION_STEP_PERCENT)
    for _ in range(steps_needed):
        tracking_service.simulate_step(session, mission.id)
    session.commit()

    assert mission.progress_percent == 100.0
    assert referral.status == ReferralStatus.ARRIVED
    assert mission.arrived_at is not None


def test_simulate_step_raises_once_already_arrived(session, two_hospitals, available_ambulance):
    referral, mission = _make_dispatched_mission(session, two_hospitals)

    steps_needed = math.ceil(100 / SIMULATION_STEP_PERCENT)
    for _ in range(steps_needed):
        tracking_service.simulate_step(session, mission.id)

    assert mission.progress_percent == 100.0
    with pytest.raises(ValueError):
        tracking_service.simulate_step(session, mission.id)


def test_simulate_step_moves_ambulance_toward_destination(session, two_hospitals, available_ambulance):
    referral, mission = _make_dispatched_mission(session, two_hospitals)
    start_lat = available_ambulance.current_latitude

    tracking_service.simulate_step(session, mission.id)

    assert available_ambulance.current_latitude != start_lat
