"""
Ambulance fleet queries and assignment logic.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from config.settings import FUEL_PENALTY_WEIGHT_PER_PERCENT, MIN_FUEL_PERCENT_FOR_ASSIGNMENT
from database.models import (
    Ambulance,
    AmbulanceStatus,
    AssignmentMethod,
    Mission,
    Referral,
    ReferralStatus,
)
from services.cost_service import estimate_trip_cost, haversine_km


def list_ambulances(
    session: Session,
    status: AmbulanceStatus | None = None,
    base_hospital_id: str | None = None,
) -> list[Ambulance]:
    query = session.query(Ambulance)
    if status is not None:
        query = query.filter(Ambulance.status == status)
    if base_hospital_id is not None:
        query = query.filter(Ambulance.base_hospital_id == base_hospital_id)
    return query.order_by(Ambulance.plate_number).all()


def get_ambulance(session: Session, ambulance_id: str) -> Ambulance | None:
    return session.get(Ambulance, ambulance_id)


def find_nearest_available(
    session: Session,
    latitude: float,
    longitude: float,
    vehicle_type=None,
) -> list[tuple[Ambulance, float]]:
    """Available ambulances scored by distance + a fuel penalty, ascending (best first)."""
    query = session.query(Ambulance).filter(
        Ambulance.status == AmbulanceStatus.AVAILABLE,
        Ambulance.fuel_level_percent >= MIN_FUEL_PERCENT_FOR_ASSIGNMENT,
        Ambulance.is_active.is_(True),
    )
    if vehicle_type is not None:
        query = query.filter(Ambulance.vehicle_type == vehicle_type)

    scored: list[tuple[Ambulance, float, float]] = []
    for amb in query.all():
        distance_km = haversine_km(latitude, longitude, amb.current_latitude, amb.current_longitude)
        fuel_penalty = (100.0 - amb.fuel_level_percent) * FUEL_PENALTY_WEIGHT_PER_PERCENT
        score = distance_km + fuel_penalty
        scored.append((amb, score, distance_km))

    scored.sort(key=lambda item: item[1])
    return [(amb, distance_km) for amb, _score, distance_km in scored]


def _create_mission(
    session: Session,
    referral: Referral,
    ambulance: Ambulance,
    assignment_method: AssignmentMethod,
    assigned_by_user_id: str | None,
) -> Mission:
    pickup = referral.referring_hospital
    destination = referral.receiving_hospital
    distance_km = haversine_km(pickup.latitude, pickup.longitude, destination.latitude, destination.longitude)
    cost = estimate_trip_cost(distance_km, ambulance.fuel_efficiency_km_per_litre)

    mission = Mission(
        referral_id=referral.id,
        ambulance_id=ambulance.id,
        assigned_by_user_id=assigned_by_user_id,
        assignment_method=assignment_method,
        pickup_latitude=pickup.latitude,
        pickup_longitude=pickup.longitude,
        destination_latitude=destination.latitude,
        destination_longitude=destination.longitude,
        distance_km=distance_km,
        estimated_fuel_litres=cost.fuel_litres,
        estimated_fuel_cost_kes=cost.fuel_cost_kes,
        estimated_operating_cost_kes=cost.operating_cost_kes,
        estimated_total_cost_kes=cost.total_cost_kes,
        progress_percent=0.0,
    )
    session.add(mission)

    referral.status = ReferralStatus.AMBULANCE_DISPATCHED
    referral.dispatched_at = datetime.utcnow()
    ambulance.status = AmbulanceStatus.ON_TRANSFER
    ambulance.current_latitude = pickup.latitude
    ambulance.current_longitude = pickup.longitude
    session.add(referral)
    session.add(ambulance)
    session.flush()
    return mission


def auto_assign_ambulance(session: Session, referral_id: str, assigned_by_user_id: str | None) -> Mission:
    referral = session.get(Referral, referral_id)
    if referral is None:
        raise ValueError("Referral not found")
    if referral.status != ReferralStatus.REFERRED:
        raise ValueError("Referral is not awaiting ambulance assignment")

    pickup = referral.referring_hospital
    candidates = find_nearest_available(session, pickup.latitude, pickup.longitude)
    if not candidates:
        raise ValueError("No available ambulance meets assignment criteria (status/fuel)")

    ambulance, _distance_km = candidates[0]
    return _create_mission(session, referral, ambulance, AssignmentMethod.AUTO, assigned_by_user_id)


def manual_assign_ambulance(
    session: Session, referral_id: str, ambulance_id: str, assigned_by_user_id: str | None
) -> Mission:
    referral = session.get(Referral, referral_id)
    if referral is None:
        raise ValueError("Referral not found")
    if referral.status != ReferralStatus.REFERRED:
        raise ValueError("Referral is not awaiting ambulance assignment")

    ambulance = session.get(Ambulance, ambulance_id)
    if ambulance is None:
        raise ValueError("Ambulance not found")
    if ambulance.status != AmbulanceStatus.AVAILABLE:
        raise ValueError(f"Ambulance {ambulance.plate_number} is not available")

    return _create_mission(session, referral, ambulance, AssignmentMethod.MANUAL, assigned_by_user_id)


def update_ambulance_status(session: Session, ambulance_id: str, new_status: AmbulanceStatus) -> Ambulance:
    ambulance = session.get(Ambulance, ambulance_id)
    if ambulance is None:
        raise ValueError("Ambulance not found")
    ambulance.status = new_status
    session.add(ambulance)
    session.flush()
    return ambulance


def set_ambulance_position(session: Session, ambulance_id: str, latitude: float, longitude: float) -> Ambulance:
    ambulance = session.get(Ambulance, ambulance_id)
    if ambulance is None:
        raise ValueError("Ambulance not found")
    ambulance.current_latitude = latitude
    ambulance.current_longitude = longitude
    session.add(ambulance)
    session.flush()
    return ambulance
