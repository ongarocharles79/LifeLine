import pytest

from database.models import Ambulance, AmbulanceStatus, AmbulanceType, Gender, ReferralStatus
from services import ambulance_service, referral_service


def _make_referral(session, two_hospitals):
    referring, receiving = two_hospitals
    return referral_service.create_referral(
        session,
        patient_data=dict(full_name="Jane Doe", age=30, gender=Gender.FEMALE),
        referring_hospital_id=referring.id,
        receiving_hospital_id=receiving.id,
        reason="Test referral reason",
    )


def test_find_nearest_available_excludes_low_fuel(session, two_hospitals):
    referring, _ = two_hospitals
    low_fuel = Ambulance(
        plate_number="KDA 200B", vehicle_type=AmbulanceType.BASIC_LIFE_SUPPORT,
        base_hospital_id=referring.id, driver_name="Low Fuel Driver",
        status=AmbulanceStatus.AVAILABLE, current_latitude=referring.latitude,
        current_longitude=referring.longitude, fuel_level_percent=5.0,
    )
    session.add(low_fuel)
    session.flush()

    candidates = ambulance_service.find_nearest_available(session, referring.latitude, referring.longitude)
    assert low_fuel.id not in [amb.id for amb, _ in candidates]


def test_find_nearest_available_excludes_busy_ambulance(session, two_hospitals, available_ambulance):
    referring, _ = two_hospitals
    available_ambulance.status = AmbulanceStatus.ON_TRANSFER
    session.flush()

    candidates = ambulance_service.find_nearest_available(session, referring.latitude, referring.longitude)
    assert candidates == []


def test_auto_assign_ambulance_updates_statuses(session, two_hospitals, available_ambulance):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    mission = ambulance_service.auto_assign_ambulance(session, referral.id, assigned_by_user_id=None)

    assert referral.status == ReferralStatus.AMBULANCE_DISPATCHED
    assert available_ambulance.status == AmbulanceStatus.ON_TRANSFER
    assert mission.ambulance_id == available_ambulance.id
    assert mission.distance_km > 0


def test_auto_assign_ambulance_raises_when_none_available(session, two_hospitals):
    referral = _make_referral(session, two_hospitals)
    session.commit()

    with pytest.raises(ValueError):
        ambulance_service.auto_assign_ambulance(session, referral.id, assigned_by_user_id=None)


def test_manual_assign_rejects_unavailable_ambulance(session, two_hospitals, available_ambulance):
    referral = _make_referral(session, two_hospitals)
    available_ambulance.status = AmbulanceStatus.MAINTENANCE
    session.commit()

    with pytest.raises(ValueError):
        ambulance_service.manual_assign_ambulance(session, referral.id, available_ambulance.id, assigned_by_user_id=None)
