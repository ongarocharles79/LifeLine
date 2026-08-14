"""
Distance and cost estimation for referral trips.

IMPORTANT: distance is a Haversine (straight-line) estimate only. It is not
a real road distance/routing calculation. Any UI surfacing this value must
label it "Estimated straight-line distance" — real road routing/ETA is a
later-phase feature (see README "What is deferred to Phase 2+").
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from config.settings import (
    FUEL_COST_PER_LITRE_KES,
    FUEL_EFFICIENCY_KM_PER_LITRE,
    HAVERSINE_EARTH_RADIUS_KM,
    OPERATING_COST_PER_KM_KES,
    PRIVATE_TRANSPORT_COST_MULTIPLIER,
)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle straight-line distance in kilometres between two points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return HAVERSINE_EARTH_RADIUS_KM * c


@dataclass
class CostEstimate:
    distance_km: float
    fuel_litres: float
    fuel_cost_kes: float
    operating_cost_kes: float
    total_cost_kes: float

    @property
    def baseline_private_transport_cost_kes(self) -> float:
        """Illustrative-only comparison figure, used for the demo 'estimated savings' KPI."""
        return self.total_cost_kes * PRIVATE_TRANSPORT_COST_MULTIPLIER


def estimate_trip_cost(
    distance_km: float,
    fuel_efficiency_km_per_litre: float = FUEL_EFFICIENCY_KM_PER_LITRE,
) -> CostEstimate:
    fuel_efficiency = fuel_efficiency_km_per_litre or FUEL_EFFICIENCY_KM_PER_LITRE
    fuel_litres = distance_km / fuel_efficiency
    fuel_cost_kes = fuel_litres * FUEL_COST_PER_LITRE_KES
    operating_cost_kes = distance_km * OPERATING_COST_PER_KM_KES
    total_cost_kes = fuel_cost_kes + operating_cost_kes
    return CostEstimate(
        distance_km=distance_km,
        fuel_litres=fuel_litres,
        fuel_cost_kes=fuel_cost_kes,
        operating_cost_kes=operating_cost_kes,
        total_cost_kes=total_cost_kes,
    )


def estimate_referral_cost(
    referring_lat: float,
    referring_lon: float,
    receiving_lat: float,
    receiving_lon: float,
    fuel_efficiency_km_per_litre: float = FUEL_EFFICIENCY_KM_PER_LITRE,
) -> CostEstimate:
    distance_km = haversine_km(referring_lat, referring_lon, receiving_lat, receiving_lon)
    return estimate_trip_cost(distance_km, fuel_efficiency_km_per_litre)
