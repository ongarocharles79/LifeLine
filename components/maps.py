"""
Pydeck map builders for the facilities/fleet overview map and the active
mission map.

IMPORTANT: ambulance positions are simulated demo data (see
services/tracking_service.py), not real GPS. This module only renders
whatever coordinates it is given.
"""
from __future__ import annotations

import pandas as pd
import pydeck as pdk

from config.settings import (
    AMBULANCE_STATUS_RGB,
    DEFAULT_MAP_ZOOM,
    FACILITY_TYPE_RGB,
    KISUMU_CENTER_LAT,
    KISUMU_CENTER_LON,
)

# Map tooltips are deliberately self-contained (fixed dark surface + white
# text, matching config/theme.py's DARK_TOKENS surface/ink) so they stay
# readable regardless of the page's active light/dark theme.
_TOOLTIP_BG = "#1E293B"
_TOOLTIP_STYLE = {"backgroundColor": _TOOLTIP_BG, "color": "#F1F5F9", "fontSize": "12px"}

_TOOLTIP_FACILITY = {
    "html": "<b>{name}</b><br/>{facility_type}<br/>Beds: {bed_capacity}<br/>{address}",
    "style": _TOOLTIP_STYLE,
}

_TOOLTIP_AMBULANCE = {
    "html": "<b>{plate_number}</b><br/>Driver: {driver_name}<br/>Status: {status}<br/>Fuel: {fuel_level_percent}%",
    "style": _TOOLTIP_STYLE,
}


def _facility_color(facility_type: str) -> list[int]:
    return FACILITY_TYPE_RGB.get(facility_type, [100, 116, 139])


def _ambulance_color(status: str) -> list[int]:
    return AMBULANCE_STATUS_RGB.get(status, [100, 116, 139])


def build_facilities_layer(hospitals_df: pd.DataFrame) -> pdk.Layer:
    df = hospitals_df.copy()
    df["color"] = df["facility_type"].apply(_facility_color)
    return pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=180,
        radius_min_pixels=5,
        radius_max_pixels=14,
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=1,
    )


def build_ambulance_layer(ambulances_df: pd.DataFrame) -> pdk.Layer:
    df = ambulances_df.copy()
    df["color"] = df["status"].apply(_ambulance_color)
    return pdk.Layer(
        "ScatterplotLayer",
        data=df,
        get_position=["current_longitude", "current_latitude"],
        get_fill_color="color",
        get_radius=140,
        radius_min_pixels=6,
        radius_max_pixels=12,
        pickable=True,
        stroked=True,
        get_line_color=[15, 23, 42],
        line_width_min_pixels=1.5,
    )


def build_route_layer(
    pickup: tuple[float, float], ambulance_pos: tuple[float, float], destination: tuple[float, float]
) -> list[pdk.Layer]:
    """pickup/ambulance_pos/destination are (lat, lon) tuples."""
    traveled = pd.DataFrame([{
        "from_lon": pickup[1], "from_lat": pickup[0],
        "to_lon": ambulance_pos[1], "to_lat": ambulance_pos[0],
    }])
    remaining = pd.DataFrame([{
        "from_lon": ambulance_pos[1], "from_lat": ambulance_pos[0],
        "to_lon": destination[1], "to_lat": destination[0],
    }])
    traveled_layer = pdk.Layer(
        "LineLayer",
        data=traveled,
        get_source_position=["from_lon", "from_lat"],
        get_target_position=["to_lon", "to_lat"],
        get_color=[37, 99, 235, 220],
        get_width=5,
    )
    remaining_layer = pdk.Layer(
        "LineLayer",
        data=remaining,
        get_source_position=["from_lon", "from_lat"],
        get_target_position=["to_lon", "to_lat"],
        get_color=[148, 163, 184, 160],
        get_width=3,
    )
    return [traveled_layer, remaining_layer]


def _view_state(latitude: float = KISUMU_CENTER_LAT, longitude: float = KISUMU_CENTER_LON, zoom: float = DEFAULT_MAP_ZOOM) -> pdk.ViewState:
    return pdk.ViewState(latitude=latitude, longitude=longitude, zoom=zoom, pitch=0)


def render_overview_map(hospitals_df: pd.DataFrame, ambulances_df: pd.DataFrame) -> pdk.Deck:
    layers = [build_facilities_layer(hospitals_df), build_ambulance_layer(ambulances_df)]
    return pdk.Deck(
        layers=layers,
        initial_view_state=_view_state(),
        map_style="light",
        tooltip=_TOOLTIP_AMBULANCE,
    )


def render_mission_map(
    pickup_name: str, pickup_lat: float, pickup_lon: float,
    destination_name: str, destination_lat: float, destination_lon: float,
    ambulance_lat: float, ambulance_lon: float, plate_number: str,
    is_emergency: bool = False,
) -> pdk.Deck:
    # Pickup = emerald (matches AVAILABLE/COMPLETED semantics), destination =
    # indigo (matches the ARRIVED status color). Red is intentionally not
    # used for either — it's reserved for genuine emergency-priority
    # signaling (the ambulance marker's outline below), not for routine
    # pickup/destination geography.
    points_df = pd.DataFrame([
        {"name": pickup_name, "kind": "Pickup (Referring Hospital)", "latitude": pickup_lat, "longitude": pickup_lon,
         "color": [5, 150, 105]},
        {"name": destination_name, "kind": "Destination (Receiving Hospital)", "latitude": destination_lat, "longitude": destination_lon,
         "color": [99, 102, 241]},
    ])
    ambulance_line_color = [220, 38, 38] if is_emergency else [255, 255, 255]
    ambulance_line_width = 3 if is_emergency else 2
    ambulance_df = pd.DataFrame([
        {"plate_number": plate_number, "latitude": ambulance_lat, "longitude": ambulance_lon, "color": [59, 130, 246]},
    ])

    point_layer = pdk.Layer(
        "ScatterplotLayer",
        data=points_df,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=220,
        radius_min_pixels=8,
        radius_max_pixels=16,
        pickable=True,
        stroked=True,
        get_line_color=[255, 255, 255],
        line_width_min_pixels=2,
    )
    ambulance_layer = pdk.Layer(
        "ScatterplotLayer",
        data=ambulance_df,
        get_position=["longitude", "latitude"],
        get_fill_color="color",
        get_radius=260,
        radius_min_pixels=10,
        radius_max_pixels=20,
        pickable=True,
        stroked=True,
        get_line_color=ambulance_line_color,
        line_width_min_pixels=ambulance_line_width,
    )
    route_layers = build_route_layer((pickup_lat, pickup_lon), (ambulance_lat, ambulance_lon), (destination_lat, destination_lon))

    mid_lat = (pickup_lat + destination_lat) / 2
    mid_lon = (pickup_lon + destination_lon) / 2

    return pdk.Deck(
        layers=[*route_layers, point_layer, ambulance_layer],
        initial_view_state=_view_state(latitude=mid_lat, longitude=mid_lon, zoom=DEFAULT_MAP_ZOOM),
        map_style="light",
        tooltip={"html": "<b>{name}{plate_number}</b>", "style": _TOOLTIP_STYLE},
    )
