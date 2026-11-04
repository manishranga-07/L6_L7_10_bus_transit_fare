import pytest
from bus_transit_fare import process_commute_manifest, inspect_smartcard_turnstiles


# ---------------------------------------------------------------------------
# Branch Coverage Tests for process_commute_manifest
# ---------------------------------------------------------------------------

def test_manifest_input_validation_branches():
    """Branch coverage for: if not isinstance(manifests, list) or booking_fee < 0"""
    # Branch 1: manifests not a list (evaluates left operand to True)
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest("invalid_manifests", 1.0)

    # Branch 2: manifests is a list, but booking_fee < 0 (evaluates right operand to True)
    with pytest.raises(ValueError, match="Invalid manifests list or booking fee"):
        process_commute_manifest([], -0.5)

    # Branch 3: manifests is a list and booking_fee >= 0 (both False, proceeds)
    result = process_commute_manifest([], 0.0)
    assert result == {"total_fare": 0.0, "status": "ZERO_RIDERSHIP"}


def test_manifest_loop_and_active_route_branches():
    """Branch coverage for: for manifest in manifests / if not manifest.get('route_active')"""
    # Loop branch: empty list -> loop not entered
    assert process_commute_manifest([], 2.0)["status"] == "ZERO_RIDERSHIP"

    # Route active: False branch -> continue
    # Route active: True branch -> proceeds
    manifests = [
        {"route_active": False, "route_type": "local"},
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [{"zones": 1, "type": "regular"}],
        },
    ]
    result = process_commute_manifest(manifests, 0.0)
    assert result["status"] == "COMPLETED"
    assert result["total_fare"] == 3.5  # 2.5 + 1.0


def test_route_type_decision_branches():
    """Branch coverage for express, shuttle, local, and invalid route_type"""
    # express route
    res_express = process_commute_manifest(
        [{"route_active": True, "route_type": "express", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert res_express["total_fare"] == 7.0  # 6.0 + 1.0

    # shuttle route
    res_shuttle = process_commute_manifest(
        [{"route_active": True, "route_type": "shuttle", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert res_shuttle["total_fare"] == 5.0  # 4.0 + 1.0

    # local route
    res_local = process_commute_manifest(
        [{"route_active": True, "route_type": "local", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert res_local["total_fare"] == 3.5  # 2.5 + 1.0

    # else branch: unknown route_type -> rejected_rides += 1, continue
    res_unknown = process_commute_manifest(
        [{"route_active": True, "route_type": "ferry", "commuters": []}],
        0.0,
    )
    assert res_unknown["status"] == "ZERO_RIDERSHIP"


def test_commuter_zones_boundary_branches():
    """Branch coverage for: if zones <= 0"""
    # zones <= 0 (True branch: rejected_rides += 1, continue)
    # zones > 0 (False branch: proceeds)
    manifests = [
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [
                {"zones": 0, "type": "regular"},
                {"zones": -2, "type": "regular"},
                {"zones": 2, "type": "regular"},
            ],
        }
    ]
    result = process_commute_manifest(manifests, 0.0)
    assert result["total_fare"] == 4.5  # 2.5 + 2.0
    assert result["status"] == "COMPLETED"


def test_blacklisted_card_and_route_branches():
    """Branch coverage for blacklisted card on express (break) vs non-express (continue)"""
    # Express route with blacklisted card: resets manifest_fare to 0.0 and breaks loop
    manifests_express = [
        {
            "route_active": True,
            "route_type": "express",
            "commuters": [
                {"zones": 2, "type": "regular", "blacklisted": False},
                {"zones": 1, "type": "regular", "blacklisted": True},
                {"zones": 3, "type": "regular", "blacklisted": False},  # skipped due to break
            ],
            "priority_boarding": False,
        }
    ]
    res_exp = process_commute_manifest(manifests_express, 0.0)
    assert res_exp["total_fare"] == 0.0
    assert res_exp["status"] == "ZERO_RIDERSHIP"

    # Non-express (local) route with blacklisted card: adds 0.0 and processes remaining commuters
    manifests_local = [
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [
                {"zones": 1, "type": "regular", "blacklisted": True},
                {"zones": 2, "type": "regular", "blacklisted": False},
            ],
            "priority_boarding": False,
        }
    ]
    res_loc = process_commute_manifest(manifests_local, 0.0)
    assert res_loc["total_fare"] == 4.5  # 2.5 + 2.0
    assert res_loc["status"] == "COMPLETED"


def test_passenger_concession_types_branches():
    """Branch coverage for: student, senior, and regular commuter types"""
    # Student: (base_seat + zones * 0.5) * 0.50
    # On express (base 6.0), zones=2 -> (6.0 + 1.0) * 0.50 = 3.50
    # Senior: (base_seat + zones * 0.5) * 0.70
    # On express (base 6.0), zones=4 -> (6.0 + 2.0) * 0.70 = 5.60
    # Regular: base_seat + zones * 1.0
    # On express (base 6.0), zones=1 -> 6.0 + 1.0 = 7.00
    manifests = [
        {
            "route_active": True,
            "route_type": "express",
            "commuters": [
                {"zones": 2, "type": "student", "blacklisted": False},
                {"zones": 4, "type": "senior", "blacklisted": False},
                {"zones": 1, "type": "regular", "blacklisted": False},
            ],
            "priority_boarding": False,
        }
    ]
    result = process_commute_manifest(manifests, 0.0)
    assert result["total_fare"] == 16.10  # 3.50 + 5.60 + 7.00
    assert result["status"] == "COMPLETED"


def test_priority_boarding_branches():
    """Branch coverage for: if manifest.get('priority_boarding', False) True and False"""
    # True branch: booking_fee added
    res_priority = process_commute_manifest(
        [{
            "route_active": True,
            "route_type": "shuttle",
            "commuters": [{"zones": 1, "type": "regular"}],
            "priority_boarding": True,
        }],
        3.50,
    )
    assert res_priority["total_fare"] == 8.50  # 4.0 + 1.0 + 3.50

    # False branch: booking_fee not added
    res_no_priority = process_commute_manifest(
        [{
            "route_active": True,
            "route_type": "shuttle",
            "commuters": [{"zones": 1, "type": "regular"}],
            "priority_boarding": False,
        }],
        3.50,
    )
    assert res_no_priority["total_fare"] == 5.00  # 4.0 + 1.0


def test_manifest_final_status_branches():
    """Branch coverage for AUDIT_REJECTED, ZERO_RIDERSHIP, and COMPLETED statuses"""
    # 1. AUDIT_REJECTED branch: rejected_rides > 4
    rejected_manifests = [
        {"route_active": True, "route_type": "invalid_1"},
        {"route_active": True, "route_type": "invalid_2"},
        {"route_active": True, "route_type": "invalid_3"},
        {"route_active": True, "route_type": "invalid_4"},
        {"route_active": True, "route_type": "invalid_5"},
    ]
    res_audit = process_commute_manifest(rejected_manifests, 1.0)
    assert res_audit["status"] == "AUDIT_REJECTED"

    # Boundary test: exactly 4 rejected rides (does NOT trigger AUDIT_REJECTED)
    boundary_manifests = [
        {"route_active": True, "route_type": "invalid_1"},
        {"route_active": True, "route_type": "invalid_2"},
        {"route_active": True, "route_type": "invalid_3"},
        {"route_active": True, "route_type": "invalid_4"},
        {
            "route_active": True,
            "route_type": "local",
            "commuters": [{"zones": 1, "type": "regular"}],
        },
    ]
    res_boundary = process_commute_manifest(boundary_manifests, 0.0)
    assert res_boundary["status"] == "COMPLETED"

    # 2. ZERO_RIDERSHIP branch: rejected_rides <= 4 and total_fare == 0.0
    res_zero = process_commute_manifest([], 0.0)
    assert res_zero["status"] == "ZERO_RIDERSHIP"
    assert res_zero["total_fare"] == 0.0

    # 3. COMPLETED branch: rejected_rides <= 4 and total_fare > 0.0
    res_completed = process_commute_manifest(
        [{"route_active": True, "route_type": "local", "commuters": [{"zones": 1, "type": "regular"}]}],
        0.0,
    )
    assert res_completed["status"] == "COMPLETED"


# ---------------------------------------------------------------------------
# Branch Coverage Tests for inspect_smartcard_turnstiles
# ---------------------------------------------------------------------------

def test_turnstiles_empty_or_falsy_branches():
    """Branch coverage for: if not turnstile_matrix (True and False branches)"""
    # True branch: empty list or None
    assert inspect_smartcard_turnstiles([]) == "NO_DATA"
    assert inspect_smartcard_turnstiles(None) == "NO_DATA"

    # False branch with empty device reading (inner loop not entered)
    assert inspect_smartcard_turnstiles([[]]) == "OPERATIONAL"


def test_turnstiles_jam_consecutive_failures_branch():
    """Branch coverage for failures > 3 and tap_failure_streak >= 2"""
    # Consecutive failures: 4 (>3, streak=1), 5 (>3, streak=2 -> returns TURNSTILE_JAM)
    readings = [[1, 4, 5, 2]]
    assert inspect_smartcard_turnstiles(readings) == "TURNSTILE_JAM"


def test_turnstiles_streak_reset_and_operational_branch():
    """Branch coverage for failures <= 3 resetting streak to 0, and completing all devices"""
    # Device 1 has an isolated failure > 3 (streak=1), then resets when failure <= 3 (3 <= 3)
    # Device 2 has no failures > 3
    # Both devices finish without streak >= 2 -> returns OPERATIONAL
    readings = [
        [4, 3, 4, 1],
        [0, 2, 3, 2],
    ]
    assert inspect_smartcard_turnstiles(readings) == "OPERATIONAL"
