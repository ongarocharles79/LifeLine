import math

from services.cost_service import estimate_trip_cost, haversine_km


def test_haversine_zero_distance_for_identical_points():
    assert haversine_km(-0.09, 34.76, -0.09, 34.76) == 0.0


def test_haversine_known_distance_kisumu_to_nairobi():
    # Kisumu (-0.0917, 34.7680) to Nairobi (-1.2921, 36.8219) is ~265 km great-circle.
    distance = haversine_km(-0.0917, 34.7680, -1.2921, 36.8219)
    assert 250 < distance < 280


def test_haversine_is_symmetric():
    a = haversine_km(-0.05, 34.70, -0.15, 34.80)
    b = haversine_km(-0.15, 34.80, -0.05, 34.70)
    assert math.isclose(a, b, rel_tol=1e-9)


def test_estimate_trip_cost_formula():
    estimate = estimate_trip_cost(distance_km=80.0, fuel_efficiency_km_per_litre=8.0)
    assert math.isclose(estimate.fuel_litres, 10.0)
    assert estimate.fuel_cost_kes > 0
    assert estimate.operating_cost_kes > 0
    assert math.isclose(estimate.total_cost_kes, estimate.fuel_cost_kes + estimate.operating_cost_kes)


def test_estimate_trip_cost_zero_distance():
    estimate = estimate_trip_cost(distance_km=0.0)
    assert estimate.fuel_litres == 0.0
    assert estimate.total_cost_kes == 0.0
