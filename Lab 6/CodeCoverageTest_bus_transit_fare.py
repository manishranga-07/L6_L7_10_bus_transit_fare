import pytest
from bus_transit_fare import process_commute_manifest, inspect_smartcard_turnstiles


def test_invalid_manifests_type_raises():
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest("invalid_type", 1.0)


def test_negative_booking_fee_raises():
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest([], -1.0)


def test_inactive_route_skipped():
    manifests = [{"route_active": False}]
    result = process_commute_manifest(manifests, 2.0)
    assert result == {"total_fare": 0.0, "status": "ZERO_RIDERSHIP"}


def test_express_student_and_blacklist_break():
    manifests = [
        {
            "route_active": True,
            "route_type": "express",
            "commuters": [
                {"zones": 2, "type": "student", "blacklisted": False},
                {"zones": 1, "type": "regular", "blacklisted": True},
            ],
            "priority_boarding": False,
        }
    ]
    result = process_commute_manifest(manifests, 2.0)
    assert result["total_fare"] == 0.0
    assert result["status"] == "ZERO_RIDERSHIP"


def test_shuttle_senior_and_invalid_zones():
    manifests = [
        {
            "route_active": True,
            "route_type": "shuttle",
            "commuters": [
                {"zones": 2, "type": "senior", "blacklisted": False},
                {"zones": 0, "type": "regular", "blacklisted": False},
            ],
            "priority_boarding": False,
        }
    ]
    result = process_commute_manifest(manifests, 2.0)
    # (4.0 + 2 * 0.5) * 0.70 = 5.0 * 0.70 = 3.50
    assert result["total_fare"] == 3.50
    assert result["status"] == "COMPLETED"


def test_unsupported_route_type_rejected():
    manifests = [
        {
            "route_active": True,
            "route_type": "monorail",
            "commuters": [],
        }
    ]
    result = process_commute_manifest(manifests, 1.0)
    assert result["status"] == "ZERO_RIDERSHIP"


def test_local_regular_passenger_and_priority_and_local_blacklisted():
    manifests = [
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [
                {"zones": 2, "type": "regular", "blacklisted": False},
                {"zones": 1, "type": "regular", "blacklisted": True},
            ],
            "priority_boarding": True,
        }
    ]
    # base 2.5 + (2 * 1.0) = 4.5. blacklisted = +0.0. priority = +2.5 => total = 7.0
    result = process_commute_manifest(manifests, 2.5)
    assert result["total_fare"] == 7.0
    assert result["status"] == "COMPLETED"


def test_audit_rejected_on_more_than_four_rejections():
    manifests = [
        {"route_active": True, "route_type": "unknown_route"} for _ in range(5)
    ]
    result = process_commute_manifest(manifests, 1.0)
    assert result["status"] == "AUDIT_REJECTED"


def test_inspect_turnstiles_no_data():
    assert inspect_smartcard_turnstiles([]) == "NO_DATA"


def test_inspect_turnstiles_jam():
    # Streak of 2 failures (>3) in a device reading
    readings = [[0, 1, 4, 5]]
    assert inspect_smartcard_turnstiles(readings) == "TURNSTILE_JAM"


def test_inspect_turnstiles_operational_with_streak_reset():
    # Failure > 3 followed by <= 3 resets streak, completes all devices
    readings = [[4, 2, 4, 1], [0, 0, 3]]
    assert inspect_smartcard_turnstiles(readings) == "OPERATIONAL"
