from collections import defaultdict
from datetime import datetime

from supabase import Client

from .datetime_utils import parse_iso_datetime, utc_now
from .logger import get_logger
from .types import SessionRawRow, SessionMetricsRow

logger = get_logger(__name__)


class SupabaseQueryError(Exception):
    """Raised when a Supabase query fails."""
    pass


def fetch_all_sessions(client: Client) -> list[SessionRawRow]:
    """Fetch all rows from sessions_raw with pagination."""
    all_rows: list[SessionRawRow] = []
    page_size = 1000
    offset = 0

    while True:
        response = client.table("sessions_raw").select("*").range(offset, offset + page_size - 1).execute()

        if response.data is None:
            raise SupabaseQueryError("Failed to fetch sessions_raw data")

        rows: list[SessionRawRow] = response.data
        all_rows.extend(rows)

        if len(rows) < page_size:
            break

        offset += page_size

    return all_rows


def compute_metrics_for_employees(
    sessions: list[SessionRawRow],
    now_utc: datetime,
) -> list[SessionMetricsRow]:
    """Compute session metrics grouped by employee_id."""
    employee_data: dict[str, dict] = defaultdict(lambda: {
        "completed_count": 0,
        "cancelled_count": 0,
        "max_completed_end_at": None,
    })

    for session in sessions:
        emp_id = session["employee_id"]
        status = session["status"]

        if status == "completed":
            employee_data[emp_id]["completed_count"] += 1
            end_at = parse_iso_datetime(session.get("end_at"))
            if end_at:
                current_max = employee_data[emp_id]["max_completed_end_at"]
                if current_max is None or end_at > current_max:
                    employee_data[emp_id]["max_completed_end_at"] = end_at

        elif status == "cancelled":
            employee_data[emp_id]["cancelled_count"] += 1

    computed_at_str = now_utc.isoformat()
    metrics: list[SessionMetricsRow] = []

    for emp_id, data in employee_data.items():
        days_since: int | None = None
        max_end = data["max_completed_end_at"]

        if max_end is not None:
            delta = now_utc - max_end
            days_since = max(0, delta.days)

        metrics.append({
            "employee_id": emp_id,
            "completed_count": data["completed_count"],
            "cancelled_count": data["cancelled_count"],
            "days_since_last_completed": days_since,
            "computed_at": computed_at_str,
        })

    return metrics


def upsert_session_metrics(client: Client, metrics: list[SessionMetricsRow]) -> None:
    """Upsert computed metrics into session_metrics table."""
    if not metrics:
        return

    response = client.table("session_metrics").upsert(
        metrics,
        on_conflict="employee_id",
    ).execute()

    if response.data is None:
        raise SupabaseQueryError("Failed to upsert session_metrics data")


def run_session_metrics_pipeline(client: Client) -> int:
    """
    Main entry function: fetch sessions, compute metrics, upsert results.
    Returns the number of employees processed.
    """
    logger.info("Starting session metrics pipeline")

    sessions = fetch_all_sessions(client)
    logger.info(f"Fetched {len(sessions)} sessions")
    if sessions:
        logger.debug(f"First row sample: {sessions[0]}")

    now_utc = utc_now()
    metrics = compute_metrics_for_employees(sessions, now_utc)
    logger.info(f"Computed metrics for {len(metrics)} employees")

    upsert_session_metrics(client, metrics)
    logger.info("Successfully upserted metrics to database")

    return len(metrics)
