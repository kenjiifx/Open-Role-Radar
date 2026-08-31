from enum import StrEnum


class CareerLevel(StrEnum):
    INTERNSHIP = "internship"
    CO_OP = "co_op"
    NEW_GRAD = "new_grad"
    ENTRY_LEVEL = "entry_level"
    APPRENTICESHIP = "apprenticeship"
    GRADUATE_PROGRAM = "graduate_program"
    ROTATIONAL_PROGRAM = "rotational_program"
    RESEARCH_INTERNSHIP = "research_internship"
    FELLOWSHIP = "fellowship"
    STUDENT_PROGRAM = "student_program"
    UNKNOWN = "unknown"


class EmploymentType(StrEnum):
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    TEMPORARY = "temporary"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


class WorkplaceType(StrEnum):
    ONSITE = "onsite"
    HYBRID = "hybrid"
    REMOTE = "remote"
    UNKNOWN = "unknown"


class RemoteScope(StrEnum):
    WORLDWIDE = "worldwide"
    COUNTRY_LIMITED = "country_limited"
    REGION_LIMITED = "region_limited"
    TIMEZONE_LIMITED = "timezone_limited"
    LOCATION_LIMITED = "location_limited"
    UNKNOWN = "unknown"


class AcademicTerm(StrEnum):
    WINTER = "winter"
    SPRING = "spring"
    SUMMER = "summer"
    FALL = "fall"
    ROLLING = "rolling"
    OFF_CYCLE = "off_cycle"
    UNKNOWN = "unknown"


class CompensationPeriod(StrEnum):
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"
    INTERNSHIP = "internship"
    UNKNOWN = "unknown"


class EvidenceStatus(StrEnum):
    CONFIRMED = "confirmed"
    NOT_AVAILABLE = "not_available"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"


class JobLifecycle(StrEnum):
    OPEN = "open"
    SUSPECTED_CLOSED = "suspected_closed"
    CLOSED = "closed"
    REOPENED = "reopened"
    QUARANTINED = "quarantined"


class EventType(StrEnum):
    OPENED = "OPENED"
    UPDATED = "UPDATED"
    CLOSED = "CLOSED"
    REOPENED = "REOPENED"


class SourceHealth(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILING = "failing"
    BLOCKED = "blocked"
    UNSUPPORTED = "unsupported"
    DISABLED = "disabled"


class PollTier(StrEnum):
    HOT = "hot"
    WARM = "warm"
    COLD = "cold"
    DORMANT = "dormant"


class EligibilityMatch(StrEnum):
    EXPLICIT_MATCH = "explicit_match"
    POTENTIAL_MATCH = "potential_match"
    UNKNOWN = "unknown"
    EXPLICITLY_INELIGIBLE = "explicitly_ineligible"
