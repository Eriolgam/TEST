"""Core domain logic for the vacation planner."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

def current_date() -> date:
    """Return today's date.

    This helper exists so that tests can monkeypatch the current date without affecting
    the standard library ``date`` class.
    """

    return date.today()


class RestrictionError(RuntimeError):
    """Raised when a vacation request violates a restriction."""


@dataclass
class VacationRequest:
    """Represents a vacation booking."""

    user: str
    start_date: date
    end_date: date

    def duration(self) -> int:
        """Return the number of vacation days (inclusive)."""

        return (self.end_date - self.start_date).days + 1

    def overlaps(self, other: "VacationRequest") -> bool:
        """Return ``True`` when two requests overlap."""

        return not (self.end_date < other.start_date or self.start_date > other.end_date)


@dataclass
class UserProfile:
    """Configuration of a user's vacation allowances and restrictions."""

    name: str
    group: str
    annual_quota: int
    blackout_ranges: Sequence[Tuple[date, date]] = field(default_factory=tuple)
    min_notice_days: int = 0

    def validate_request(self, request: VacationRequest, existing: Iterable[VacationRequest]) -> None:
        """Validate the request against individual restrictions."""

        if request.user != self.name:
            raise RestrictionError("Request user does not match profile")

        if request.start_date > request.end_date:
            raise RestrictionError("The start date must be before the end date")

        if self.min_notice_days:
            days_until_start = (request.start_date - current_date()).days
            if days_until_start < self.min_notice_days:
                raise RestrictionError(
                    f"Requests must be submitted at least {self.min_notice_days} days in advance"
                )

        for start, end in self.blackout_ranges:
            if not (request.end_date < start or request.start_date > end):
                raise RestrictionError("Request conflicts with a blackout period")

        requested_days_this_year = sum(
            r.duration()
            for r in existing
            if r.user == self.name and r.start_date.year == request.start_date.year
        )
        if requested_days_this_year + request.duration() > self.annual_quota:
            raise RestrictionError("Annual quota exceeded")


@dataclass
class GroupRestriction:
    """Limits the number of users from a group that can be on vacation simultaneously."""

    group: str
    max_simultaneous: int


class VacationPlanner:
    """Manages vacation requests for multiple users."""

    def __init__(
        self,
        *,
        global_blackout_ranges: Optional[Sequence[Tuple[date, date]]] = None,
        global_allowed_months: Optional[Sequence[int]] = None,
    ) -> None:
        self._users: Dict[str, UserProfile] = {}
        self._group_restrictions: Dict[str, GroupRestriction] = {}
        self._requests: List[VacationRequest] = []
        self._global_blackout_ranges = list(global_blackout_ranges or [])
        self._global_allowed_months = set(global_allowed_months or [])

    # ------------------------------------------------------------------
    # configuration helpers
    # ------------------------------------------------------------------
    def add_user(self, profile: UserProfile) -> None:
        """Register a new user profile."""

        self._users[profile.name] = profile

    def add_group_restriction(self, restriction: GroupRestriction) -> None:
        """Configure a restriction for a group."""

        self._group_restrictions[restriction.group] = restriction

    def iter_requests(self) -> Iterable[VacationRequest]:
        """Iterate over all existing requests."""

        yield from sorted(self._requests, key=lambda r: (r.start_date, r.user))

    # ------------------------------------------------------------------
    # booking logic
    # ------------------------------------------------------------------
    def request_vacation(self, user: str, start_date: date, end_date: date) -> VacationRequest:
        """Add a vacation request after validating all restrictions."""

        if user not in self._users:
            raise RestrictionError(f"Unknown user: {user}")

        request = VacationRequest(user=user, start_date=start_date, end_date=end_date)
        self._validate(request)
        self._requests.append(request)
        return request

    # ------------------------------------------------------------------
    # validation helpers
    # ------------------------------------------------------------------
    def _validate(self, request: VacationRequest) -> None:
        profile = self._users[request.user]
        profile.validate_request(request, self._requests)
        self._validate_global_rules(request)
        self._validate_group_rules(request, profile)

    def _validate_global_rules(self, request: VacationRequest) -> None:
        if self._global_allowed_months and request.start_date.month not in self._global_allowed_months:
            raise RestrictionError("Requested start date is outside of the allowed months")

        for start, end in self._global_blackout_ranges:
            if not (request.end_date < start or request.start_date > end):
                raise RestrictionError("Requested vacation falls within a global blackout period")

    def _validate_group_rules(self, request: VacationRequest, profile: UserProfile) -> None:
        restriction = self._group_restrictions.get(profile.group)
        if restriction is None:
            return

        overlapping = sum(
            1
            for existing in self._requests
            if existing.user != request.user
            and self._users[existing.user].group == profile.group
            and existing.overlaps(request)
        )

        if overlapping >= restriction.max_simultaneous:
            raise RestrictionError(
                "Group capacity reached for the requested period"
            )

    # ------------------------------------------------------------------
    # reporting helpers
    # ------------------------------------------------------------------
    def calendar_for_year(self, year: int) -> Dict[str, List[VacationRequest]]:
        """Return all requests for the given year grouped by user."""

        calendar: Dict[str, List[VacationRequest]] = {name: [] for name in self._users}
        for request in self._requests:
            if request.start_date.year == year or request.end_date.year == year:
                calendar.setdefault(request.user, []).append(request)
        for requests in calendar.values():
            requests.sort(key=lambda r: r.start_date)
        return calendar

    def availability(self, start_date: date, end_date: date, group: Optional[str] = None) -> Dict[str, int]:
        """Return the remaining capacity per group for the given range."""

        availability: Dict[str, int] = {}
        for grp, restriction in self._group_restrictions.items():
            if group is not None and grp != group:
                continue
            overlapping = sum(
                1
                for request in self._requests
                if self._users[request.user].group == grp and request.overlaps(VacationRequest("", start_date, end_date))
            )
            availability[grp] = max(restriction.max_simultaneous - overlapping, 0)
        return availability


def daterange(start: date, end: date) -> Iterable[date]:
    """Yield each day within an inclusive date range."""

    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)
