"""
Referral lifecycle management: creation, status transitions, handover
completion, and dashboard KPI computation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from config.settings import PRIVATE_TRANSPORT_COST_MULTIPLIER
from database.models import (
    Ambulance,
    AmbulanceStatus,
    Handover,
    Hospital,
    Mission,
    Patient,
    PatientCondition,
    Referral,
    ReferralPriority,
    ReferralStatus,
)
from services.cost_service import estimate_referral_cost

# Legal referral status transitions. Cancellation is allowed from any
# non-terminal state and is handled separately in cancel_referral().
_TRANSITIONS: dict[ReferralStatus, set[ReferralStatus]] = {
    ReferralStatus.REFERRED: {ReferralStatus.AMBULANCE_DISPATCHED},
    ReferralStatus.AMBULANCE_DISPATCHED: {ReferralStatus.PATIENT_PICKED_UP},
    ReferralStatus.PATIENT_PICKED_UP: {ReferralStatus.TRANSPORTING},
    ReferralStatus.TRANSPORTING: {ReferralStatus.ARRIVED},
    ReferralStatus.ARRIVED: {ReferralStatus.COMPLETED},
}

_TIMESTAMP_FIELD: dict[ReferralStatus, str] = {
    ReferralStatus.AMBULANCE_DISPATCHED: "dispatched_at",
    ReferralStatus.PATIENT_PICKED_UP: "picked_up_at",
    ReferralStatus.TRANSPORTING: "transporting_at",
    ReferralStatus.ARRIVED: "arrived_at",
    ReferralStatus.COMPLETED: "completed_at",
}

_TERMINAL_STATUSES = {ReferralStatus.COMPLETED, ReferralStatus.CANCELLED}


def create_referral(
    session: Session,
    patient_data: dict,
    referring_hospital_id: str,
    receiving_hospital_id: str,
    reason: str,
    clinical_notes: str | None = None,
    medical_history: str | None = None,
    current_medications: str | None = None,
    allergies: str | None = None,
    referring_physician: str | None = None,
    receiving_physician: str | None = None,
    priority: ReferralPriority = ReferralPriority.URGENT,
    referring_staff_id: str | None = None,
) -> Referral:
    if referring_hospital_id == receiving_hospital_id:
        raise ValueError("Referring and receiving hospital must be different")

    referring_hospital = session.get(Hospital, referring_hospital_id)
    receiving_hospital = session.get(Hospital, receiving_hospital_id)
    if referring_hospital is None or receiving_hospital is None:
        raise ValueError("Referring or receiving hospital not found")

    patient = Patient(**patient_data)
    session.add(patient)
    session.flush()

    cost = estimate_referral_cost(
        referring_hospital.latitude, referring_hospital.longitude,
        receiving_hospital.latitude, receiving_hospital.longitude,
    )

    referral = Referral(
        patient_id=patient.id,
        referring_hospital_id=referring_hospital_id,
        receiving_hospital_id=receiving_hospital_id,
        referring_staff_id=referring_staff_id,
        referring_physician=referring_physician,
        receiving_physician=receiving_physician,
        reason=reason,
        clinical_notes=clinical_notes,
        medical_history=medical_history,
        current_medications=current_medications,
        allergies=allergies,
        priority=priority,
        status=ReferralStatus.REFERRED,
        estimated_distance_km=cost.distance_km,
        estimated_cost_kes=cost.total_cost_kes,
    )
    session.add(referral)
    session.flush()
    return referral


def list_referrals(
    session: Session,
    status: ReferralStatus | None = None,
    priority: ReferralPriority | None = None,
    hospital_id: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[Referral]:
    query = session.query(Referral)
    if status is not None:
        query = query.filter(Referral.status == status)
    if priority is not None:
        query = query.filter(Referral.priority == priority)
    if hospital_id is not None:
        query = query.filter(
            (Referral.referring_hospital_id == hospital_id)
            | (Referral.receiving_hospital_id == hospital_id)
        )
    if date_from is not None:
        query = query.filter(Referral.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Referral.created_at <= date_to)
    return query.order_by(Referral.created_at.desc()).all()


def get_referral(session: Session, referral_id: str) -> Referral | None:
    return session.get(Referral, referral_id)


def get_active_referrals(session: Session) -> list[Referral]:
    return (
        session.query(Referral)
        .filter(~Referral.status.in_(_TERMINAL_STATUSES))
        .order_by(Referral.created_at.desc())
        .all()
    )


def advance_referral_status(session: Session, referral_id: str, new_status: ReferralStatus) -> Referral:
    referral = session.get(Referral, referral_id)
    if referral is None:
        raise ValueError("Referral not found")

    allowed = _TRANSITIONS.get(referral.status, set())
    if new_status not in allowed:
        raise ValueError(f"Cannot move referral from {referral.status.value} to {new_status.value}")

    referral.status = new_status
    field = _TIMESTAMP_FIELD.get(new_status)
    if field:
        setattr(referral, field, datetime.utcnow())
    session.add(referral)
    session.flush()
    return referral


def cancel_referral(session: Session, referral_id: str, reason: str) -> Referral:
    referral = session.get(Referral, referral_id)
    if referral is None:
        raise ValueError("Referral not found")
    if referral.status in _TERMINAL_STATUSES:
        raise ValueError("Referral is already in a terminal state")

    referral.status = ReferralStatus.CANCELLED
    referral.cancelled_at = datetime.utcnow()
    referral.clinical_notes = f"{referral.clinical_notes or ''}\n[Cancelled: {reason}]".strip()

    if referral.mission is not None:
        ambulance = session.get(Ambulance, referral.mission.ambulance_id)
        if ambulance is not None:
            ambulance.status = AmbulanceStatus.AVAILABLE
            session.add(ambulance)

    session.add(referral)
    session.flush()
    return referral


def complete_handover(
    session: Session,
    referral_id: str,
    vitals: dict,
    interventions: str | None,
    medications_administered: str | None,
    notes: str | None,
    patient_condition: PatientCondition,
    received_by_user_id: str | None,
) -> Handover:
    referral = session.get(Referral, referral_id)
    if referral is None:
        raise ValueError("Referral not found")
    if referral.status != ReferralStatus.ARRIVED:
        raise ValueError("Handover can only be completed for a referral that has Arrived")
    if referral.mission is None:
        raise ValueError("Referral has no associated mission")

    handover = Handover(
        referral_id=referral.id,
        mission_id=referral.mission.id,
        received_by_user_id=received_by_user_id,
        receiving_hospital_id=referral.receiving_hospital_id,
        patient_condition_on_arrival=patient_condition,
        interventions=interventions,
        medications_administered=medications_administered,
        notes=notes,
        **vitals,
    )
    session.add(handover)

    referral.status = ReferralStatus.COMPLETED
    referral.completed_at = datetime.utcnow()
    session.add(referral)

    mission = referral.mission
    mission.completed_at = datetime.utcnow()
    session.add(mission)

    ambulance = session.get(Ambulance, mission.ambulance_id)
    if ambulance is not None:
        ambulance.status = AmbulanceStatus.AVAILABLE
        session.add(ambulance)

    session.flush()
    return handover


@dataclass
class ReferralKPIs:
    total_referrals: int
    active_referrals: int
    available_ambulances: int
    avg_response_time_minutes: float | None
    completion_rate_percent: float
    total_fuel_cost_kes: float
    total_distance_km: float
    estimated_savings_kes: float
    fleet_efficiency_percent: float


def compute_kpis(session: Session) -> ReferralKPIs:
    total_referrals = session.query(func.count(Referral.id)).scalar() or 0
    active_referrals = (
        session.query(func.count(Referral.id))
        .filter(~Referral.status.in_(_TERMINAL_STATUSES))
        .scalar()
        or 0
    )
    available_ambulances = (
        session.query(func.count(Ambulance.id))
        .filter(Ambulance.status == AmbulanceStatus.AVAILABLE)
        .scalar()
        or 0
    )
    total_ambulances = session.query(func.count(Ambulance.id)).scalar() or 0
    completed_referrals = (
        session.query(func.count(Referral.id))
        .filter(Referral.status == ReferralStatus.COMPLETED)
        .scalar()
        or 0
    )

    completion_rate_percent = (completed_referrals / total_referrals * 100) if total_referrals else 0.0

    # Computed in Python (rather than SQL) to avoid relying on a
    # SQLite-specific date-diff function, keeping this query portable.
    dispatch_gaps = (
        session.query(Referral.created_at, Referral.dispatched_at)
        .filter(Referral.dispatched_at.isnot(None))
        .all()
    )
    if dispatch_gaps:
        avg_response_time_minutes = sum(
            (dispatched_at - created_at).total_seconds() / 60 for created_at, dispatched_at in dispatch_gaps
        ) / len(dispatch_gaps)
    else:
        avg_response_time_minutes = None

    total_fuel_cost_kes = session.query(func.coalesce(func.sum(Mission.estimated_fuel_cost_kes), 0.0)).scalar() or 0.0
    total_distance_km = session.query(func.coalesce(func.sum(Mission.distance_km), 0.0)).scalar() or 0.0
    total_operating_cost_kes = (
        session.query(func.coalesce(func.sum(Mission.estimated_operating_cost_kes), 0.0)).scalar() or 0.0
    )
    total_trip_cost_kes = total_fuel_cost_kes + total_operating_cost_kes

    # Illustrative-only heuristic: compares actual fleet cost against a
    # private-transport cost multiplier baseline. Not a validated benchmark.
    estimated_savings_kes = total_trip_cost_kes * (PRIVATE_TRANSPORT_COST_MULTIPLIER - 1)

    # "Fleet efficiency" here means the share of the fleet currently in active use.
    active_ambulances = (
        session.query(func.count(Ambulance.id))
        .filter(Ambulance.status == AmbulanceStatus.ON_TRANSFER)
        .scalar()
        or 0
    )
    fleet_efficiency_percent = (active_ambulances / total_ambulances * 100) if total_ambulances else 0.0

    return ReferralKPIs(
        total_referrals=total_referrals,
        active_referrals=active_referrals,
        available_ambulances=available_ambulances,
        avg_response_time_minutes=avg_response_time_minutes,
        completion_rate_percent=completion_rate_percent,
        total_fuel_cost_kes=total_fuel_cost_kes,
        total_distance_km=total_distance_km,
        estimated_savings_kes=estimated_savings_kes,
        fleet_efficiency_percent=fleet_efficiency_percent,
    )
