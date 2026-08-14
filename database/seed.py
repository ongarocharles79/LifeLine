"""
Idempotent demo data seeding for LIFELINE Phase 1.

run(session) populates: 4 demo users, ~40 Kisumu-area hospitals, 22 demo
ambulances, and ~30 days of historical referrals/missions/handovers/
location updates, plus a handful of "live" in-progress referrals reserved
for today so the Live Tracking page has material to demo immediately.

All patient, driver, and physician names are fictional. All facility
coordinates are demo/seed placements — see data/seed_data.py.

Safe to call on every app startup: it no-ops if hospitals already exist.
"""
from __future__ import annotations

import random
import string
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from config.settings import AVERAGE_SPEED_KMH, DEMO_ACCOUNTS
from data.seed_data import (
    CLINICAL_CONDITIONS,
    FACILITY_NAME_SUFFIXES,
    HANDOVER_NOTE_TEMPLATES,
    INTERVENTION_TEMPLATES,
    KENYAN_FIRST_NAMES,
    KENYAN_SURNAMES,
    KISUMU_CENTER_LAT,
    KISUMU_CENTER_LON,
    MAJOR_HOSPITALS,
    MEDICATION_TEMPLATES,
    REFERRAL_REASON_TEMPLATES,
    WARD_NAMES,
)
from database.models import (
    Ambulance,
    AmbulanceStatus,
    AmbulanceType,
    AssignmentMethod,
    FacilityType,
    Gender,
    Handover,
    Hospital,
    LocationUpdate,
    Mission,
    MissionStatus,
    Patient,
    PatientCondition,
    Referral,
    ReferralPriority,
    ReferralStatus,
    User,
    UserRole,
)
from services.auth_service import hash_password
from services.cost_service import estimate_trip_cost, haversine_km

_RNG_SEED = 42
_AMBULANCE_COUNT = 22
_PLATE_LETTERS = "BCDT"
_KISUMU_SUB_COUNTIES = [
    "Kisumu Central", "Kisumu East", "Kisumu West", "Nyando", "Muhoroni", "Nyakach", "Seme",
]


def run(session: Session) -> None:
    """Seed demo data if the database is empty. Safe to call repeatedly."""
    if session.query(Hospital).count() > 0:
        return

    random.seed(_RNG_SEED)

    users = _seed_users(session)
    hospitals = _seed_hospitals(session)
    ambulances = _seed_ambulances(session, hospitals)
    session.flush()

    _seed_referral_history(session, hospitals, ambulances, users)
    _finalize_ambulance_statuses(ambulances)

    session.commit()


# --------------------------------------------------------------------------
# Users
# --------------------------------------------------------------------------

def _seed_users(session: Session) -> list[User]:
    users = []
    for account in DEMO_ACCOUNTS:
        user = User(
            email=account["email"],
            password_hash=hash_password(account["password"]),
            role=UserRole(account["role"]),
            full_name=account["full_name"],
            phone=account.get("phone"),
        )
        session.add(user)
        users.append(user)
    session.flush()
    return users


# --------------------------------------------------------------------------
# Hospitals
# --------------------------------------------------------------------------

def _random_phone() -> str:
    return f"+2547{random.randint(10000000, 99999999)}"


def _jitter_coordinates(spread: float = 0.09) -> tuple[float, float]:
    lat = KISUMU_CENTER_LAT + random.uniform(-spread, spread)
    lon = KISUMU_CENTER_LON + random.uniform(-spread, spread)
    return lat, lon


def _seed_hospitals(session: Session) -> list[Hospital]:
    hospitals: list[Hospital] = []

    for h in MAJOR_HOSPITALS:
        hospital = Hospital(
            name=h["name"],
            facility_type=FacilityType(h["facility_type"]),
            level=h.get("level"),
            latitude=h["latitude"],
            longitude=h["longitude"],
            address=h.get("address"),
            sub_county=h.get("sub_county"),
            phone=_random_phone(),
            bed_capacity=h.get("bed_capacity"),
            has_emergency_unit=h.get("has_emergency_unit", False),
            has_icu=h.get("has_icu", False),
        )
        session.add(hospital)
        hospitals.append(hospital)

    for ward in WARD_NAMES:
        suffix = random.choice(FACILITY_NAME_SUFFIXES)
        is_health_centre = suffix == "Health Centre"
        lat, lon = _jitter_coordinates()
        hospital = Hospital(
            name=f"{ward} {suffix}",
            facility_type=FacilityType.HEALTH_CENTRE if is_health_centre else FacilityType.DISPENSARY,
            level=3 if is_health_centre else 2,
            latitude=lat,
            longitude=lon,
            address=f"{ward}, Kisumu County",
            sub_county=random.choice(_KISUMU_SUB_COUNTIES),
            phone=_random_phone(),
            bed_capacity=random.randint(6, 30),
            has_emergency_unit=False,
            has_icu=False,
        )
        session.add(hospital)
        hospitals.append(hospital)

    session.flush()
    return hospitals


# --------------------------------------------------------------------------
# Ambulances
# --------------------------------------------------------------------------

def _generate_plate(existing: set[str]) -> str:
    while True:
        plate = (
            f"K{random.choice(_PLATE_LETTERS)}{random.choice(string.ascii_uppercase)} "
            f"{random.randint(100, 999)}{random.choice(string.ascii_uppercase)}"
        )
        if plate not in existing:
            existing.add(plate)
            return plate


def _generate_driver_name(existing: set[str]) -> str:
    while True:
        name = f"{random.choice(KENYAN_FIRST_NAMES)} {random.choice(KENYAN_SURNAMES)}"
        if name not in existing:
            existing.add(name)
            return name


def _seed_ambulances(session: Session, hospitals: list[Hospital]) -> list[Ambulance]:
    emergency_hospitals = [h for h in hospitals if h.has_emergency_unit]
    plates: set[str] = set()
    driver_names: set[str] = set()
    ambulances: list[Ambulance] = []

    for _ in range(_AMBULANCE_COUNT):
        base = random.choice(emergency_hospitals)
        vehicle_type = random.choices(
            [AmbulanceType.BASIC_LIFE_SUPPORT, AmbulanceType.ADVANCED_LIFE_SUPPORT, AmbulanceType.PATIENT_TRANSPORT],
            weights=[60, 25, 15],
        )[0]
        ambulance = Ambulance(
            plate_number=_generate_plate(plates),
            vehicle_type=vehicle_type,
            base_hospital_id=base.id,
            driver_name=_generate_driver_name(driver_names),
            driver_phone=_random_phone(),
            status=AmbulanceStatus.AVAILABLE,
            current_latitude=base.latitude,
            current_longitude=base.longitude,
            fuel_level_percent=round(random.uniform(40, 100), 1),
            fuel_tank_capacity_litres=random.choice([50.0, 60.0, 70.0]),
            fuel_efficiency_km_per_litre=round(random.uniform(6.5, 9.5), 2),
            year=random.randint(2014, 2023),
        )
        session.add(ambulance)
        ambulances.append(ambulance)

    session.flush()
    return ambulances


def _finalize_ambulance_statuses(ambulances: list[Ambulance]) -> None:
    """Distribute On Break / Maintenance across ambulances not already
    committed to a live mission (those are already On Transfer)."""
    remaining = [a for a in ambulances if a.status == AmbulanceStatus.AVAILABLE]
    random.shuffle(remaining)
    for amb in remaining[:2]:
        amb.status = AmbulanceStatus.MAINTENANCE
    for amb in remaining[2:4]:
        amb.status = AmbulanceStatus.ON_BREAK


# --------------------------------------------------------------------------
# Patients
# --------------------------------------------------------------------------

def _make_patient() -> Patient:
    gender = random.choice([Gender.MALE, Gender.FEMALE])
    return Patient(
        full_name=f"{random.choice(KENYAN_FIRST_NAMES)} {random.choice(KENYAN_SURNAMES)}",
        age=random.randint(1, 90),
        gender=gender,
        condition=random.choice(CLINICAL_CONDITIONS),
        phone=_random_phone(),
    )


# --------------------------------------------------------------------------
# Referral / mission / handover history
# --------------------------------------------------------------------------

def _seed_referral_history(
    session: Session, hospitals: list[Hospital], ambulances: list[Ambulance], users: list[User]
) -> None:
    receiving_pool = [h for h in hospitals if h.has_icu]
    staff_user = next(u for u in users if u.role == UserRole.STAFF)
    admin_user = next(u for u in users if u.role == UserRole.ADMIN)
    now = datetime.utcnow()

    # Historical days: fully terminal outcomes only (completed / arrived-only / cancelled).
    for day_offset in range(29, 1, -1):
        for _ in range(random.randint(2, 6)):
            _create_terminal_referral(session, hospitals, receiving_pool, ambulances, staff_user, now, day_offset)

    # Yesterday + today: background terminal referrals plus a few reserved live ones.
    for day_offset in (1, 0):
        for _ in range(random.randint(2, 5)):
            _create_terminal_referral(session, hospitals, receiving_pool, ambulances, staff_user, now, day_offset)

    _create_live_referrals(session, hospitals, receiving_pool, ambulances, staff_user, admin_user, now)
    session.flush()


def _create_terminal_referral(
    session: Session,
    hospitals: list[Hospital],
    receiving_pool: list[Hospital],
    ambulances: list[Ambulance],
    staff_user: User,
    now: datetime,
    day_offset: int,
) -> None:
    receiving = random.choice(receiving_pool)
    referring = random.choice([h for h in hospitals if h.id != receiving.id])

    patient = _make_patient()
    session.add(patient)
    session.flush()

    cost = estimate_trip_cost(
        haversine_km(referring.latitude, referring.longitude, receiving.latitude, receiving.longitude)
    )
    created_at = now - timedelta(days=day_offset, hours=random.randint(0, 23), minutes=random.randint(0, 59))
    priority = random.choices(
        [ReferralPriority.EMERGENCY, ReferralPriority.URGENT, ReferralPriority.ROUTINE],
        weights=[30, 45, 25],
    )[0]

    referral = Referral(
        patient_id=patient.id,
        referring_hospital_id=referring.id,
        receiving_hospital_id=receiving.id,
        referring_staff_id=staff_user.id,
        referring_physician=f"Dr. {random.choice(KENYAN_SURNAMES)}",
        receiving_physician=f"Dr. {random.choice(KENYAN_SURNAMES)}",
        reason=random.choice(REFERRAL_REASON_TEMPLATES),
        clinical_notes=patient.condition,
        priority=priority,
        status=ReferralStatus.REFERRED,
        estimated_distance_km=cost.distance_km,
        estimated_cost_kes=cost.total_cost_kes,
        created_at=created_at,
    )
    session.add(referral)
    session.flush()

    outcome_roll = random.random()
    if outcome_roll < 0.05:
        referral.status = ReferralStatus.CANCELLED
        referral.cancelled_at = created_at + timedelta(minutes=random.randint(5, 30))
        return

    ambulance = random.choice(ambulances)
    dispatched_at = created_at + timedelta(minutes=random.randint(5, 15))
    picked_up_at = dispatched_at + timedelta(minutes=random.randint(10, 20))
    transporting_at = picked_up_at + timedelta(minutes=random.randint(2, 5))
    travel_minutes = max(5.0, cost.distance_km / AVERAGE_SPEED_KMH * 60)
    arrived_at = transporting_at + timedelta(minutes=travel_minutes)

    referral.status = ReferralStatus.AMBULANCE_DISPATCHED
    referral.dispatched_at = dispatched_at
    referral.picked_up_at = picked_up_at
    referral.transporting_at = transporting_at

    mission = Mission(
        referral_id=referral.id,
        ambulance_id=ambulance.id,
        assignment_method=random.choices([AssignmentMethod.AUTO, AssignmentMethod.MANUAL], weights=[80, 20])[0],
        pickup_latitude=referring.latitude,
        pickup_longitude=referring.longitude,
        destination_latitude=receiving.latitude,
        destination_longitude=receiving.longitude,
        distance_km=cost.distance_km,
        estimated_fuel_litres=cost.fuel_litres,
        estimated_fuel_cost_kes=cost.fuel_cost_kes,
        estimated_operating_cost_kes=cost.operating_cost_kes,
        estimated_total_cost_kes=cost.total_cost_kes,
        progress_percent=100.0,
        status=MissionStatus.ARRIVED,
        started_at=dispatched_at,
        arrived_at=arrived_at,
    )
    session.add(mission)
    session.flush()

    steps = [0, 25, 50, 75, 100]
    step_span = (arrived_at - dispatched_at) / max(len(steps) - 1, 1)
    for i, pct in enumerate(steps):
        frac = pct / 100.0
        lat = referring.latitude + (receiving.latitude - referring.latitude) * frac
        lon = referring.longitude + (receiving.longitude - referring.longitude) * frac
        session.add(LocationUpdate(
            mission_id=mission.id,
            ambulance_id=ambulance.id,
            latitude=lat,
            longitude=lon,
            progress_percent=pct,
            distance_remaining_km=haversine_km(lat, lon, receiving.latitude, receiving.longitude),
            speed_kmh_assumed=AVERAGE_SPEED_KMH,
            recorded_at=dispatched_at + step_span * i,
        ))

    referral.arrived_at = arrived_at
    referral.status = ReferralStatus.ARRIVED

    if outcome_roll < 0.15:
        # Left "arrived, awaiting handover" for status-mix variety.
        session.flush()
        return

    completed_at = arrived_at + timedelta(minutes=random.randint(10, 30))
    mission.completed_at = completed_at
    mission.status = MissionStatus.COMPLETED

    session.add(Handover(
        referral_id=referral.id,
        mission_id=mission.id,
        received_by_user_id=staff_user.id,
        receiving_hospital_id=receiving.id,
        blood_pressure_systolic=random.randint(90, 160),
        blood_pressure_diastolic=random.randint(60, 100),
        heart_rate_bpm=random.randint(60, 120),
        temperature_celsius=round(random.uniform(36.0, 39.5), 1),
        spo2_percent=random.randint(88, 100),
        respiratory_rate=random.randint(12, 28),
        blood_glucose_mmol_l=round(random.uniform(4.0, 9.0), 1),
        interventions=random.choice(INTERVENTION_TEMPLATES),
        medications_administered=random.choice(MEDICATION_TEMPLATES),
        notes=random.choice(HANDOVER_NOTE_TEMPLATES),
        patient_condition_on_arrival=random.choices(
            [PatientCondition.STABLE, PatientCondition.IMPROVED, PatientCondition.CRITICAL, PatientCondition.DECEASED],
            weights=[60, 30, 8, 2],
        )[0],
        handover_at=completed_at,
    ))

    referral.status = ReferralStatus.COMPLETED
    referral.completed_at = completed_at


def _create_live_referrals(
    session: Session,
    hospitals: list[Hospital],
    receiving_pool: list[Hospital],
    ambulances: list[Ambulance],
    staff_user: User,
    admin_user: User,
    now: datetime,
) -> None:
    """Reserve a handful of referrals in various non-terminal states so the
    Referrals/Live Tracking pages have immediate demo material, while
    leaving most of the fleet Available for the user to assign themselves."""
    used_ambulance_ids: set[str] = set()

    def _pick_ambulance() -> Ambulance:
        for amb in ambulances:
            if amb.id not in used_ambulance_ids and amb.status == AmbulanceStatus.AVAILABLE:
                used_ambulance_ids.add(amb.id)
                return amb
        raise RuntimeError("Not enough available ambulances to seed live demo referrals")

    # Two referrals left awaiting ambulance assignment.
    _live_at_status(session, hospitals, receiving_pool, staff_user, now, ReferralStatus.REFERRED)
    _live_at_status(session, hospitals, receiving_pool, staff_user, now, ReferralStatus.REFERRED)

    _live_at_status(
        session, hospitals, receiving_pool, staff_user, now, ReferralStatus.AMBULANCE_DISPATCHED,
        ambulance=_pick_ambulance(), progress_percent=0.0, assigned_by=admin_user,
    )
    _live_at_status(
        session, hospitals, receiving_pool, staff_user, now, ReferralStatus.PATIENT_PICKED_UP,
        ambulance=_pick_ambulance(), progress_percent=20.0, assigned_by=admin_user,
    )
    _live_at_status(
        session, hospitals, receiving_pool, staff_user, now, ReferralStatus.TRANSPORTING,
        ambulance=_pick_ambulance(), progress_percent=50.0, assigned_by=admin_user,
    )


def _live_at_status(
    session: Session,
    hospitals: list[Hospital],
    receiving_pool: list[Hospital],
    staff_user: User,
    now: datetime,
    status: ReferralStatus,
    ambulance: Ambulance | None = None,
    progress_percent: float = 0.0,
    assigned_by: User | None = None,
) -> Referral:
    receiving = random.choice(receiving_pool)
    referring = random.choice([h for h in hospitals if h.id != receiving.id])

    patient = _make_patient()
    session.add(patient)
    session.flush()

    cost = estimate_trip_cost(
        haversine_km(referring.latitude, referring.longitude, receiving.latitude, receiving.longitude)
    )
    created_at = now - timedelta(hours=random.randint(1, 5))

    referral = Referral(
        patient_id=patient.id,
        referring_hospital_id=referring.id,
        receiving_hospital_id=receiving.id,
        referring_staff_id=staff_user.id,
        referring_physician=f"Dr. {random.choice(KENYAN_SURNAMES)}",
        receiving_physician=f"Dr. {random.choice(KENYAN_SURNAMES)}",
        reason=random.choice(REFERRAL_REASON_TEMPLATES),
        clinical_notes=patient.condition,
        priority=random.choice([ReferralPriority.EMERGENCY, ReferralPriority.URGENT]),
        status=ReferralStatus.REFERRED,
        estimated_distance_km=cost.distance_km,
        estimated_cost_kes=cost.total_cost_kes,
        created_at=created_at,
    )
    session.add(referral)
    session.flush()

    if status == ReferralStatus.REFERRED:
        return referral

    dispatched_at = created_at + timedelta(minutes=10)
    referral.status = ReferralStatus.AMBULANCE_DISPATCHED
    referral.dispatched_at = dispatched_at

    fraction = progress_percent / 100.0
    current_lat = referring.latitude + (receiving.latitude - referring.latitude) * fraction
    current_lon = referring.longitude + (receiving.longitude - referring.longitude) * fraction

    mission = Mission(
        referral_id=referral.id,
        ambulance_id=ambulance.id,
        assigned_by_user_id=assigned_by.id if assigned_by else None,
        assignment_method=AssignmentMethod.AUTO,
        pickup_latitude=referring.latitude,
        pickup_longitude=referring.longitude,
        destination_latitude=receiving.latitude,
        destination_longitude=receiving.longitude,
        distance_km=cost.distance_km,
        estimated_fuel_litres=cost.fuel_litres,
        estimated_fuel_cost_kes=cost.fuel_cost_kes,
        estimated_operating_cost_kes=cost.operating_cost_kes,
        estimated_total_cost_kes=cost.total_cost_kes,
        progress_percent=progress_percent,
        status=MissionStatus.EN_ROUTE if progress_percent > 0 else MissionStatus.DISPATCHED,
        started_at=dispatched_at,
    )
    session.add(mission)
    session.flush()

    ambulance.status = AmbulanceStatus.ON_TRANSFER
    ambulance.current_latitude = current_lat
    ambulance.current_longitude = current_lon
    session.add(ambulance)

    if progress_percent > 0:
        session.add(LocationUpdate(
            mission_id=mission.id,
            ambulance_id=ambulance.id,
            latitude=current_lat,
            longitude=current_lon,
            progress_percent=progress_percent,
            distance_remaining_km=haversine_km(current_lat, current_lon, receiving.latitude, receiving.longitude),
            speed_kmh_assumed=AVERAGE_SPEED_KMH,
            recorded_at=dispatched_at + timedelta(minutes=15),
        ))

    if status in (ReferralStatus.PATIENT_PICKED_UP, ReferralStatus.TRANSPORTING):
        referral.status = ReferralStatus.PATIENT_PICKED_UP
        referral.picked_up_at = dispatched_at + timedelta(minutes=15)

    if status == ReferralStatus.TRANSPORTING:
        referral.status = ReferralStatus.TRANSPORTING
        referral.transporting_at = dispatched_at + timedelta(minutes=20)

    return referral
