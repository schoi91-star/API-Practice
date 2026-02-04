from typing import TypedDict


class SessionRawRow(TypedDict):
    session_id: str
    employee_id: str
    status: str
    start_at: str
    end_at: str | None
    created_at: str


class SessionMetricsRow(TypedDict):
    employee_id: str
    completed_count: int
    cancelled_count: int
    days_since_last_completed: int | None
    computed_at: str
