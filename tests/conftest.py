import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Ambulance, AmbulanceStatus, AmbulanceType, Base, FacilityType, Hospital


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    s = SessionLocal()
    yield s
    s.close()


@pytest.fixture()
def two_hospitals(session):
    referring = Hospital(
        name="Test Referring Health Centre",
        facility_type=FacilityType.HEALTH_CENTRE,
        latitude=-0.05, longitude=34.70,
        has_emergency_unit=False, has_icu=False,
    )
    receiving = Hospital(
        name="Test Receiving Referral Hospital",
        facility_type=FacilityType.COUNTY_REFERRAL,
        latitude=-0.15, longitude=34.80,
        has_emergency_unit=True, has_icu=True,
    )
    session.add_all([referring, receiving])
    session.flush()
    return referring, receiving


@pytest.fixture()
def available_ambulance(session, two_hospitals):
    referring, _ = two_hospitals
    amb = Ambulance(
        plate_number="KDA 100A",
        vehicle_type=AmbulanceType.BASIC_LIFE_SUPPORT,
        base_hospital_id=referring.id,
        driver_name="Test Driver",
        status=AmbulanceStatus.AVAILABLE,
        current_latitude=referring.latitude,
        current_longitude=referring.longitude,
        fuel_level_percent=80.0,
    )
    session.add(amb)
    session.flush()
    return amb
