"""
SQLAlchemy 2.0 declarative models for LIFELINE Phase 1.

Design notes:
- All primary keys are string UUIDs (`String(36)`), not native/Postgres UUID
  types, and all enums are mapped with `native_enum=False` (plain VARCHAR).
  This keeps the schema identical across SQLite (Phase 1) and Postgres
  (a later phase) with no migration rewrite needed.
- Hospital/ambulance relationships use real foreign keys, never free-text
  hospital names, per the Phase 1 spec.
- `referral.status` is the canonical workflow state; `mission.status` mirrors
  it for convenient mission-scoped querying.
"""
from __future__ import annotations

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _enum(enum_cls, **kwargs):
    return SAEnum(enum_cls, native_enum=False, length=32, **kwargs)


# --------------------------------------------------------------------------
# Enums
# --------------------------------------------------------------------------

class UserRole(str, enum.Enum):
    ADMIN = "ADMIN"
    STAFF = "STAFF"
    DRIVER = "DRIVER"
    MANAGER = "MANAGER"


class FacilityType(str, enum.Enum):
    NATIONAL_REFERRAL = "NATIONAL_REFERRAL"
    COUNTY_REFERRAL = "COUNTY_REFERRAL"
    SUB_COUNTY_HOSPITAL = "SUB_COUNTY_HOSPITAL"
    HEALTH_CENTRE = "HEALTH_CENTRE"
    DISPENSARY = "DISPENSARY"
    PRIVATE_HOSPITAL = "PRIVATE_HOSPITAL"
    MISSION_HOSPITAL = "MISSION_HOSPITAL"


class AmbulanceType(str, enum.Enum):
    BASIC_LIFE_SUPPORT = "BASIC_LIFE_SUPPORT"
    ADVANCED_LIFE_SUPPORT = "ADVANCED_LIFE_SUPPORT"
    PATIENT_TRANSPORT = "PATIENT_TRANSPORT"


class AmbulanceStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    ON_TRANSFER = "ON_TRANSFER"
    ON_BREAK = "ON_BREAK"
    MAINTENANCE = "MAINTENANCE"
    RETURNING = "RETURNING"


class Gender(str, enum.Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class ReferralPriority(str, enum.Enum):
    EMERGENCY = "EMERGENCY"
    URGENT = "URGENT"
    ROUTINE = "ROUTINE"


class ReferralStatus(str, enum.Enum):
    REFERRED = "REFERRED"
    AMBULANCE_DISPATCHED = "AMBULANCE_DISPATCHED"
    PATIENT_PICKED_UP = "PATIENT_PICKED_UP"
    TRANSPORTING = "TRANSPORTING"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class AssignmentMethod(str, enum.Enum):
    AUTO = "AUTO"
    MANUAL = "MANUAL"


class MissionStatus(str, enum.Enum):
    DISPATCHED = "DISPATCHED"
    EN_ROUTE = "EN_ROUTE"
    ARRIVED = "ARRIVED"
    COMPLETED = "COMPLETED"


class PatientCondition(str, enum.Enum):
    STABLE = "STABLE"
    IMPROVED = "IMPROVED"
    CRITICAL = "CRITICAL"
    DECEASED = "DECEASED"


# --------------------------------------------------------------------------
# Models
# --------------------------------------------------------------------------

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(_enum(UserRole), nullable=False)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Hospital(Base):
    __tablename__ = "hospitals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    facility_type: Mapped[FacilityType] = mapped_column(_enum(FacilityType), nullable=False)
    level: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    sub_county: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bed_capacity: Mapped[int | None] = mapped_column(Integer, nullable=True)
    has_emergency_unit: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_icu: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    ambulances: Mapped[list["Ambulance"]] = relationship(back_populates="base_hospital")


class Ambulance(Base):
    __tablename__ = "ambulances"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    plate_number: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    vehicle_type: Mapped[AmbulanceType] = mapped_column(_enum(AmbulanceType), nullable=False)
    base_hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=False)
    driver_name: Mapped[str] = mapped_column(String(120), nullable=False)
    driver_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[AmbulanceStatus] = mapped_column(
        _enum(AmbulanceStatus), nullable=False, default=AmbulanceStatus.AVAILABLE, index=True
    )
    current_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_level_percent: Mapped[float] = mapped_column(Float, default=100.0, nullable=False)
    fuel_tank_capacity_litres: Mapped[float] = mapped_column(Float, default=60.0, nullable=False)
    fuel_efficiency_km_per_litre: Mapped[float] = mapped_column(Float, default=8.0, nullable=False)
    year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_service_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    base_hospital: Mapped["Hospital"] = relationship(back_populates="ambulances")
    missions: Mapped[list["Mission"]] = relationship(back_populates="ambulance")


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    gender: Mapped[Gender] = mapped_column(_enum(Gender), default=Gender.UNKNOWN, nullable=False)
    condition: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(20), nullable=True)
    next_of_kin_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    next_of_kin_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    patient_id: Mapped[str] = mapped_column(String(36), ForeignKey("patients.id"), nullable=False)
    referring_hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=False)
    receiving_hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=False)
    referring_staff_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    referring_physician: Mapped[str | None] = mapped_column(String(120), nullable=True)
    receiving_physician: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    clinical_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    medical_history: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_medications: Mapped[str | None] = mapped_column(Text, nullable=True)
    allergies: Mapped[str | None] = mapped_column(Text, nullable=True)
    priority: Mapped[ReferralPriority] = mapped_column(
        _enum(ReferralPriority), nullable=False, default=ReferralPriority.URGENT
    )
    status: Mapped[ReferralStatus] = mapped_column(
        _enum(ReferralStatus), nullable=False, default=ReferralStatus.REFERRED, index=True
    )
    estimated_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_cost_kes: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    dispatched_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    picked_up_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    transporting_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    patient: Mapped["Patient"] = relationship()
    referring_hospital: Mapped["Hospital"] = relationship(foreign_keys=[referring_hospital_id])
    receiving_hospital: Mapped["Hospital"] = relationship(foreign_keys=[receiving_hospital_id])
    referring_staff: Mapped["User | None"] = relationship(foreign_keys=[referring_staff_id])
    mission: Mapped["Mission | None"] = relationship(back_populates="referral", uselist=False)
    handover: Mapped["Handover | None"] = relationship(back_populates="referral", uselist=False)


class Mission(Base):
    __tablename__ = "missions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    referral_id: Mapped[str] = mapped_column(String(36), ForeignKey("referrals.id"), unique=True, nullable=False)
    ambulance_id: Mapped[str] = mapped_column(String(36), ForeignKey("ambulances.id"), nullable=False)
    assigned_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    assignment_method: Mapped[AssignmentMethod] = mapped_column(_enum(AssignmentMethod), nullable=False)

    pickup_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_longitude: Mapped[float] = mapped_column(Float, nullable=False)
    destination_latitude: Mapped[float] = mapped_column(Float, nullable=False)
    destination_longitude: Mapped[float] = mapped_column(Float, nullable=False)

    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_fuel_litres: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_fuel_cost_kes: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_operating_cost_kes: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_total_cost_kes: Mapped[float | None] = mapped_column(Float, nullable=True)

    progress_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[MissionStatus] = mapped_column(
        _enum(MissionStatus), nullable=False, default=MissionStatus.DISPATCHED
    )

    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    referral: Mapped["Referral"] = relationship(back_populates="mission")
    ambulance: Mapped["Ambulance"] = relationship(back_populates="missions")
    assigned_by: Mapped["User | None"] = relationship(foreign_keys=[assigned_by_user_id])
    location_updates: Mapped[list["LocationUpdate"]] = relationship(back_populates="mission")
    handover: Mapped["Handover | None"] = relationship(back_populates="mission", uselist=False)


class Handover(Base):
    __tablename__ = "handovers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    referral_id: Mapped[str] = mapped_column(String(36), ForeignKey("referrals.id"), unique=True, nullable=False)
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), nullable=False)
    received_by_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"), nullable=True)
    receiving_hospital_id: Mapped[str] = mapped_column(String(36), ForeignKey("hospitals.id"), nullable=False)

    blood_pressure_systolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_pressure_diastolic: Mapped[int | None] = mapped_column(Integer, nullable=True)
    heart_rate_bpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    temperature_celsius: Mapped[float | None] = mapped_column(Float, nullable=True)
    spo2_percent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    respiratory_rate: Mapped[int | None] = mapped_column(Integer, nullable=True)
    blood_glucose_mmol_l: Mapped[float | None] = mapped_column(Float, nullable=True)

    interventions: Mapped[str | None] = mapped_column(Text, nullable=True)
    medications_administered: Mapped[str | None] = mapped_column(Text, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    patient_condition_on_arrival: Mapped[PatientCondition] = mapped_column(
        _enum(PatientCondition), default=PatientCondition.STABLE, nullable=False
    )

    handover_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    referral: Mapped["Referral"] = relationship(back_populates="handover")
    mission: Mapped["Mission"] = relationship(back_populates="handover")
    receiving_hospital: Mapped["Hospital"] = relationship()
    received_by: Mapped["User | None"] = relationship(foreign_keys=[received_by_user_id])


class LocationUpdate(Base):
    __tablename__ = "location_updates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    mission_id: Mapped[str] = mapped_column(String(36), ForeignKey("missions.id"), nullable=False, index=True)
    ambulance_id: Mapped[str] = mapped_column(String(36), ForeignKey("ambulances.id"), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    progress_percent: Mapped[float] = mapped_column(Float, nullable=False)
    distance_remaining_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kmh_assumed: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    mission: Mapped["Mission"] = relationship(back_populates="location_updates")
