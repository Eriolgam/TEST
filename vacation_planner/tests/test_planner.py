from datetime import date, timedelta

import pytest

from vacation_planner import GroupRestriction, RestrictionError, UserProfile, VacationPlanner


def make_planner():
    planner = VacationPlanner(
        global_blackout_ranges=[(date(2024, 12, 24), date(2025, 1, 2))],
        global_allowed_months=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    )
    planner.add_group_restriction(GroupRestriction(group="engineering", max_simultaneous=2))
    planner.add_user(
        UserProfile(
            name="Alice",
            group="engineering",
            annual_quota=25,
            blackout_ranges=[(date(2024, 4, 1), date(2024, 4, 7))],
        )
    )
    planner.add_user(UserProfile(name="Bob", group="engineering", annual_quota=20))
    planner.add_user(UserProfile(name="Eve", group="engineering", annual_quota=15))
    return planner


def test_request_is_added_when_restrictions_pass():
    planner = make_planner()
    planner.request_vacation("Alice", date(2024, 3, 4), date(2024, 3, 8))
    requests = list(planner.iter_requests())
    assert len(requests) == 1
    assert requests[0].user == "Alice"


def test_individual_blackout_is_enforced():
    planner = make_planner()
    with pytest.raises(RestrictionError):
        planner.request_vacation("Alice", date(2024, 4, 2), date(2024, 4, 5))


def test_global_blackout_is_enforced():
    planner = make_planner()
    with pytest.raises(RestrictionError):
        planner.request_vacation("Alice", date(2024, 12, 26), date(2024, 12, 27))


def test_annual_quota_is_checked():
    planner = make_planner()
    planner.request_vacation("Bob", date(2024, 1, 1), date(2024, 1, 10))
    with pytest.raises(RestrictionError):
        planner.request_vacation("Bob", date(2024, 2, 1), date(2024, 2, 15))


def test_cross_year_requests_count_days_in_each_year():
    planner = make_planner()
    bob = planner._users["Bob"]
    bob.annual_quota = 10
    planner._global_allowed_months = set(range(1, 13))
    planner._global_blackout_ranges.clear()

    planner.request_vacation("Bob", date(2024, 12, 23), date(2025, 1, 10))

    with pytest.raises(RestrictionError):
        planner.request_vacation("Bob", date(2025, 1, 15), date(2025, 1, 16))


def test_group_capacity_is_respected():
    planner = make_planner()
    planner.request_vacation("Alice", date(2024, 3, 4), date(2024, 3, 8))
    planner.request_vacation("Bob", date(2024, 3, 4), date(2024, 3, 8))
    with pytest.raises(RestrictionError):
        planner.request_vacation("Eve", date(2024, 3, 5), date(2024, 3, 6))


def test_availability_counts_remaining_capacity():
    planner = make_planner()
    planner.request_vacation("Alice", date(2024, 3, 4), date(2024, 3, 8))
    availability = planner.availability(date(2024, 3, 4), date(2024, 3, 8))
    assert availability["engineering"] == 1


def test_calendar_for_year_groups_by_user():
    planner = make_planner()
    planner.request_vacation("Alice", date(2024, 3, 4), date(2024, 3, 8))
    planner.request_vacation("Bob", date(2024, 5, 1), date(2024, 5, 3))

    calendar = planner.calendar_for_year(2024)
    assert len(calendar["Alice"]) == 1
    assert len(calendar["Bob"]) == 1
    assert calendar["Alice"][0].start_date == date(2024, 3, 4)


def test_requests_outside_allowed_months_are_rejected():
    planner = make_planner()
    with pytest.raises(RestrictionError):
        planner.request_vacation("Alice", date(2024, 12, 1), date(2024, 12, 3))


def test_min_notice_period_is_respected(monkeypatch):
    planner = make_planner()
    alice = planner._users["Alice"]
    alice.min_notice_days = 30

    # Freeze "today" to 2024-02-01 for deterministic behaviour.
    monkeypatch.setattr("vacation_planner.planner.current_date", lambda: date(2024, 2, 1))

    with pytest.raises(RestrictionError):
        planner.request_vacation("Alice", date(2024, 2, 15), date(2024, 2, 16))

    planner.request_vacation("Alice", date(2024, 3, 15), date(2024, 3, 20))


def test_request_with_invalid_user_fails():
    planner = make_planner()
    with pytest.raises(RestrictionError):
        planner.request_vacation("Mallory", date(2024, 3, 1), date(2024, 3, 2))


def test_request_with_reversed_dates_fails():
    planner = make_planner()
    with pytest.raises(RestrictionError):
        planner.request_vacation("Alice", date(2024, 3, 10), date(2024, 3, 5))


def test_daterange_yields_inclusive_dates():
    from vacation_planner.planner import daterange

    start = date(2024, 3, 1)
    end = date(2024, 3, 3)
    assert list(daterange(start, end)) == [start, start + timedelta(days=1), end]
