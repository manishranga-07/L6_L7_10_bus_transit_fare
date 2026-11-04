import pytest
from bus_transit_fare import process_commute_manifest, inspect_smartcard_turnstiles

# Starter example test case:
def test_single_regular_local_ride():
    manifests = [
        {
            "route_active": True,
            "route_type": "local",
            "priority_boarding": False,
            "commuters": [{"zones": 2, "type": "regular", "blacklisted": False}]
        }
    ]
    result = process_commute_manifest(manifests, 2.0)
    assert result["total_fare"] == 4.5
    assert result["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# Additional Test Cases for Full Code & Branch Coverage (100%)
# ---------------------------------------------------------------------------

def test_manifest_validation_type_and_negative_fee():
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest("not_a_list", 1.0)
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest([], -2.0)


def test_inactive_routes_and_empty_manifest():
    assert process_commute_manifest([], 1.0) == {"total_fare": 0.0, "status": "ZERO_RIDERSHIP"}
    res = process_commute_manifest([{"route_active": False, "route_type": "local"}], 1.0)
    assert res == {"total_fare": 0.0, "status": "ZERO_RIDERSHIP"}


def test_route_types_express_shuttle_local_and_invalid():
    # Express
    exp = process_commute_manifest(
        [{"route_active": True, "route_type": "express", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert exp["total_fare"] == 7.0

    # Shuttle
    shu = process_commute_manifest(
        [{"route_active": True, "route_type": "shuttle", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert shu["total_fare"] == 5.0

    # Local
    loc = process_commute_manifest(
        [{"route_active": True, "route_type": "local", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert loc["total_fare"] == 3.5

    # Invalid route type
    inv = process_commute_manifest(
        [{"route_active": True, "route_type": "tram", "commuters": []}],
        0.0,
    )
    assert inv["status"] == "ZERO_RIDERSHIP"


def test_commuters_zones_and_blacklisted_card():
    # Invalid zones (<= 0)
    manifest_zero_zone = [
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [{"zones": 0, "type": "regular"}, {"zones": -1, "type": "regular"}],
        }
    ]
    assert process_commute_manifest(manifest_zero_zone, 0.0)["status"] == "ZERO_RIDERSHIP"

    # Blacklisted card on express (manifest_fare = 0.0 and break)
    manifest_exp_black = [
        {
            "route_active": True,
            "route_type": "express",
            "commuters": [
                {"zones": 1, "type": "regular", "blacklisted": False},
                {"zones": 1, "type": "regular", "blacklisted": True},
                {"zones": 2, "type": "regular", "blacklisted": False},
            ],
        }
    ]
    assert process_commute_manifest(manifest_exp_black, 0.0)["total_fare"] == 0.0

    # Blacklisted card on non-express (manifest_fare += 0.0)
    manifest_loc_black = [
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [
                {"zones": 1, "type": "regular", "blacklisted": True},
                {"zones": 1, "type": "regular", "blacklisted": False},
            ],
        }
    ]
    assert process_commute_manifest(manifest_loc_black, 0.0)["total_fare"] == 3.5


def test_passenger_types_student_senior_and_priority_boarding():
    manifest = [
        {
            "route_active": True,
            "route_type": "shuttle",
            "priority_boarding": True,
            "commuters": [
                {"zones": 2, "type": "student", "blacklisted": False},  # (4.0 + 1.0) * 0.5 = 2.5
                {"zones": 2, "type": "senior", "blacklisted": False},   # (4.0 + 1.0) * 0.7 = 3.5
            ],
        }
    ]
    # Fare: 2.5 + 3.5 + 2.0 (priority) = 8.0
    res = process_commute_manifest(manifest, 2.0)
    assert res["total_fare"] == 8.0
    assert res["status"] == "COMPLETED"


def test_audit_rejected_condition():
    # 5 rejections
    manifests = [{"route_active": True, "route_type": "invalid"} for _ in range(5)]
    res = process_commute_manifest(manifests, 1.0)
    assert res["status"] == "AUDIT_REJECTED"


def test_turnstiles_inspection():
    # NO_DATA
    assert inspect_smartcard_turnstiles([]) == "NO_DATA"

    # JAM (streak >= 2 with failures > 3)
    assert inspect_smartcard_turnstiles([[0, 4, 5]]) == "TURNSTILE_JAM"

    # OPERATIONAL with streak reset
    assert inspect_smartcard_turnstiles([[4, 1, 4], [0, 0]]) == "OPERATIONAL"
