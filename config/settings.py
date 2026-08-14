"""
Central configuration for LIFELINE Phase 1.

All values are overridable via environment variables / .env so that later
phases (e.g. a Postgres deployment) can change configuration without code
changes. This module is the single source of truth for cost constants,
demo accounts, map defaults, and status color mappings — do not duplicate
these values elsewhere.
"""
from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


# --- App metadata -----------------------------------------------------------
APP_NAME = "LIFELINE"
APP_TAGLINE = "Connecting Healthcare, Saving Lives Across Kisumu County"
APP_SUBTITLE = "Hospital Referral & Ambulance Tracking System"
DEMO_MODE_LABEL = "DEMO ENVIRONMENT — PHASE 1 PROTOTYPE"

# --- Database -----------------------------------------------------------
# SQLite for Phase 1. The schema (UUID string PKs, portable enum columns) is
# written so DATABASE_URL can later point at Postgres with no model changes.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./lifeline.db")

# --- Auth (Phase 1 demo scheme only — see services/auth_service.py) --------
# NOT production-grade. Structured so it can be swapped for Argon2id/OIDC
# later without changing call sites in services/auth_service.py.
AUTH_PEPPER = os.getenv("AUTH_PEPPER", "lifeline-dev-pepper-change-me")

DEMO_ACCOUNTS = [
    {
        "email": "admin@demo.lifeline",
        "password": "ChangeMe123!",
        "role": "ADMIN",
        "full_name": "Grace Achieng",
        "phone": "+254700100001",
        "facility": "LIFELINE County Operations Center",
    },
    {
        "email": "staff@demo.lifeline",
        "password": "ChangeMe123!",
        "role": "STAFF",
        "full_name": "Brian Otieno",
        "phone": "+254700100002",
        "facility": "Kisumu County Referral Hospital",
    },
    {
        "email": "driver@demo.lifeline",
        "password": "ChangeMe123!",
        "role": "DRIVER",
        "full_name": "Kevin Omondi",
        "phone": "+254700100003",
        "facility": "Jaramogi Oginga Odinga Teaching & Referral Hospital",
    },
    {
        "email": "manager@demo.lifeline",
        "password": "ChangeMe123!",
        "role": "MANAGER",
        "full_name": "Faith Adhiambo",
        "phone": "+254700100004",
        "facility": "LIFELINE County Operations Center",
    },
]

DEMO_ACCOUNT_FACILITY_BY_EMAIL = {a["email"]: a["facility"] for a in DEMO_ACCOUNTS}

# --- Cost estimation constants (services/cost_service.py) -------------------
HAVERSINE_EARTH_RADIUS_KM = 6371.0
FUEL_EFFICIENCY_KM_PER_LITRE = _float_env("FUEL_EFFICIENCY_KM_PER_LITRE", 8.0)
FUEL_COST_PER_LITRE_KES = _float_env("FUEL_COST_PER_LITRE_KES", 180.0)
OPERATING_COST_PER_KM_KES = _float_env("OPERATING_COST_PER_KM_KES", 45.0)
AVERAGE_SPEED_KMH = _float_env("AVERAGE_SPEED_KMH", 40.0)

# Illustrative baseline used only to compute the demo "estimated savings" KPI
# (comparing ambulance operating cost against a private-transport heuristic).
# This is NOT a validated real-world benchmark — label it as illustrative in UI.
PRIVATE_TRANSPORT_COST_MULTIPLIER = 1.6

# --- Ambulance assignment ---------------------------------------------------
MIN_FUEL_PERCENT_FOR_ASSIGNMENT = 20.0
FUEL_PENALTY_WEIGHT_PER_PERCENT = 0.05  # added to distance score per % fuel below 100

# --- Simulated tracking ------------------------------------------------------
SIMULATION_STEP_PERCENT = _float_env("SIMULATION_STEP_PERCENT", 20.0)

# --- Map defaults (Kisumu, Kenya) -------------------------------------------
KISUMU_CENTER_LAT = -0.0917
KISUMU_CENTER_LON = 34.7680
DEFAULT_MAP_ZOOM = 10.3

# --- Status color mappings (shared by cards/charts/maps for consistency) ----
# Healthcare-operations palette: blue = primary/in-progress, teal = clinical
# handoff states, amber/orange = dispatch/maintenance attention, indigo =
# arrival, green = success/completed, red is reserved for true emergency/
# critical signaling and is intentionally NOT used for routine states like
# "Cancelled". Tailwind "600" shades are used throughout (rather than the
# more vibrant "500" shades) because they are the ones that clear WCAG's
# 3:1 non-text contrast minimum against BOTH a white/light surface and a
# dark slate surface at once — verified numerically, not eyeballed (see
# tests / the contrast-ratio check run during the UI theming pass). Pills
# render as {color} text on a {color}+alpha tinted background.
REFERRAL_STATUS_COLORS = {
    "REFERRED": "#3B82F6",
    "AMBULANCE_DISPATCHED": "#D97706",
    "PATIENT_PICKED_UP": "#0D9488",
    "TRANSPORTING": "#3B82F6",
    "ARRIVED": "#6366F1",
    "COMPLETED": "#059669",
    "CANCELLED": "#64748B",
}

# Referral priority is real data (ReferralPriority enum, set at referral
# creation) — red is reserved exclusively for this genuine emergency signal,
# not applied decoratively elsewhere. #DC2626 (red-600) is the one red shade
# verified to clear 3:1 contrast against both a white and a dark-slate
# surface at once (see the contrast-ratio check).
PRIORITY_COLORS = {
    "EMERGENCY": "#DC2626",
    "URGENT": "#D97706",
    "ROUTINE": "#64748B",
}

AMBULANCE_STATUS_COLORS = {
    "AVAILABLE": "#059669",
    "ON_TRANSFER": "#3B82F6",
    "ON_BREAK": "#64748B",
    "MAINTENANCE": "#EA580C",
    "RETURNING": "#0D9488",
}

AMBULANCE_STATUS_RGB = {
    "AVAILABLE": [5, 150, 105],
    "ON_TRANSFER": [59, 130, 246],
    "ON_BREAK": [100, 116, 139],
    "MAINTENANCE": [234, 88, 12],
    "RETURNING": [13, 148, 136],
}

FACILITY_TYPE_RGB = {
    "NATIONAL_REFERRAL": [15, 23, 42],
    "COUNTY_REFERRAL": [29, 78, 216],
    "SUB_COUNTY_HOSPITAL": [37, 99, 235],
    "HEALTH_CENTRE": [96, 165, 250],
    "DISPENSARY": [186, 230, 253],
    "PRIVATE_HOSPITAL": [13, 148, 136],
    "MISSION_HOSPITAL": [45, 212, 191],
}
