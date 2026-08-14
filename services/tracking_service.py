"""
Simulated ambulance mission tracking.

Movement is a DEMONSTRATION simulation only: each call to simulate_step()
advances the ambulance a fixed percentage of the mission's total straight-
line distance, interpolating linearly between the pickup and destination
coordinates. This is not real GPS tracking.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from config.settings import AVERAGE_SPEED_KMH, SIMULATION_STEP_PERCENT
from database.models import LocationUpdate, Mission, MissionStatus, Referral, ReferralStatus
from services.cost_service import haversine_km
from services.referral_service import advance_referral_status


def get_active_mission(session: Session, referral_id: str) -> Mission | None:
    return session.query(Mission).filter(Mission.referral_id == referral_id).first()


def get_mission(session: Session, mission_id: str) -> Mission | None:
    return session.get(Mission, mission_id)


def mark_picked_up(session: Session, referral_id: str) -> Referral:
    return advance_referral_status(session, referral_id, ReferralStatus.PATIENT_PICKED_UP)


def mark_transporting(session: Session, referral_id: str) -> Referral:
    return advance_referral_status(session, referral_id, ReferralStatus.TRANSPORTING)


def _interpolate(start: float, end: float, fraction: float) -> float:
    return start + (end - start) * fraction


def simulate_step(session: Session, mission_id: str) -> LocationUpdate:
    """Advance the mission by SIMULATION_STEP_PERCENT of its total distance."""
    mission = session.get(Mission, mission_id)
    if mission is None:
        raise ValueError("Mission not found")
    if mission.progress_percent >= 100.0:
        raise ValueError("This mission has already arrived at its destination.")

    new_progress = min(100.0, mission.progress_percent + SIMULATION_STEP_PERCENT)
    fraction = new_progress / 100.0

    new_lat = _interpolate(mission.pickup_latitude, mission.destination_latitude, fraction)
    new_lon = _interpolate(mission.pickup_longitude, mission.destination_longitude, fraction)
    distance_remaining_km = haversine_km(
        new_lat, new_lon, mission.destination_latitude, mission.destination_longitude
    )

    location_update = LocationUpdate(
        mission_id=mission.id,
        ambulance_id=mission.ambulance_id,
        latitude=new_lat,
        longitude=new_lon,
        progress_percent=new_progress,
        distance_remaining_km=distance_remaining_km,
        speed_kmh_assumed=AVERAGE_SPEED_KMH,
    )
    session.add(location_update)

    mission.progress_percent = new_progress
    ambulance = mission.ambulance
    ambulance.current_latitude = new_lat
    ambulance.current_longitude = new_lon
    session.add(ambulance)

    if new_progress >= 100.0:
        mission.status = MissionStatus.ARRIVED
        mission.arrived_at = datetime.utcnow()
        advance_referral_status(session, mission.referral_id, ReferralStatus.ARRIVED)
    else:
        mission.status = MissionStatus.EN_ROUTE

    session.add(mission)
    session.flush()
    return location_update


def get_location_history(session: Session, mission_id: str) -> list[LocationUpdate]:
    return (
        session.query(LocationUpdate)
        .filter(LocationUpdate.mission_id == mission_id)
        .order_by(LocationUpdate.recorded_at)
        .all()
    )
