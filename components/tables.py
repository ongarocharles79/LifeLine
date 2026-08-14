"""
Dataframe/table rendering helpers, including CSV export support.
"""
from __future__ import annotations

import io

import pandas as pd
import streamlit as st

from database.models import Ambulance, Referral


def render_dataframe(df: pd.DataFrame, hide_index: bool = True) -> None:
    st.dataframe(df, width='stretch', hide_index=hide_index)


def referrals_table(referrals: list[Referral]) -> pd.DataFrame:
    rows = []
    for r in referrals:
        rows.append({
            "Created": r.created_at.strftime("%Y-%m-%d %H:%M") if r.created_at else "",
            "Patient": r.patient.full_name if r.patient else "",
            "Condition": r.patient.condition if r.patient else "",
            "From": r.referring_hospital.name if r.referring_hospital else "",
            "To": r.receiving_hospital.name if r.receiving_hospital else "",
            "Priority": r.priority.value.title() if r.priority else "",
            "Status": r.status.value.replace("_", " ").title() if r.status else "",
            "Distance (km)": round(r.estimated_distance_km, 1) if r.estimated_distance_km else None,
            "Est. Cost (KES)": round(r.estimated_cost_kes, 0) if r.estimated_cost_kes else None,
        })
    return pd.DataFrame(rows)


def ambulances_table(ambulances: list[Ambulance]) -> pd.DataFrame:
    rows = []
    for a in ambulances:
        rows.append({
            "Plate": a.plate_number,
            "Type": a.vehicle_type.value.replace("_", " ").title(),
            "Driver": a.driver_name,
            "Base Hospital": a.base_hospital.name if a.base_hospital else "",
            "Status": a.status.value.replace("_", " ").title(),
            "Fuel (%)": round(a.fuel_level_percent, 0),
            "Latitude": round(a.current_latitude, 4),
            "Longitude": round(a.current_longitude, 4),
        })
    return pd.DataFrame(rows)


def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")
