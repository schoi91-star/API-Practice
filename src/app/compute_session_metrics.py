"""
Session metrics computation module.

This module provides functions to:
1. Fetch session data from Supabase with pagination and retry logic
2. Compute per-employee metrics (completed/cancelled counts, days since last)
3. Upsert computed metrics back to Supabase

The main entry point is run_session_metrics_pipeline().
"""
import time
from collections import defaultdict
from datetime import datetime

from httpx import ConnectError, TimeoutException
from supabase import Client

from .datetime_utils import parse_iso_datetime, utc_now
from .logger import get_logger
from .types import SessionRawRow, SessionMetricsRow

logger = get_logger(__name__)


class SupabaseQueryError(Exception):
    """Raised when a Supabase query fails after all retry attempts."""
    pass


def _fetch_page_with_retry(
    client: Client,
    table_name: str,
    offset: int,
    page_size: int,
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> list[dict]:
    """
    Fetch a single page of data with retry logic.

    Uses exponential backoff: waits 1s, 2s, 4s between retries.
    Only retries on transient errors (network issues, timeouts).

    Args:
        client: Supabase client instance
        table_name: Name of the table to query
        offset: Starting row offset for pagination
        page_size: Number of rows to fetch
        max_retries: Maximum number of retry attempts (default: 3)
        base_delay: Base delay in seconds for exponential backoff (default: 1.0)

    Returns:
        List of row dictionaries from the query

    Raises:
        SupabaseQueryError: If all retry attempts fail
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.table(table_name).select("*").range(
                offset, offset + page_size - 1
            ).execute()

            if response.data is None:
                raise SupabaseQueryError(f"Failed to fetch {table_name} data: response.data is None")

            return response.data

        except (ConnectError, TimeoutException) as e:
            # Transient network errors - worth retrying
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Fetch attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} fetch attempts failed for offset {offset}")

        except Exception as e:
            # Non-transient errors (auth, schema, etc.) - don't retry
            logger.error(f"Non-retryable error fetching {table_name}: {e}")
            raise SupabaseQueryError(f"Failed to fetch {table_name}: {e}") from e

    # All retries exhausted
    raise SupabaseQueryError(
        f"Failed to fetch {table_name} after {max_retries} attempts"
    ) from last_exception


def fetch_all_sessions(
    client: Client,
    page_size: int = 1000,
    max_retries: int = 3,
) -> list[SessionRawRow]:
    """
    Fetch all rows from sessions_raw table with pagination.

    Handles large datasets by fetching in pages of page_size rows.
    Each page fetch includes retry logic for transient errors.

    Args:
        client: Supabase client instance
        page_size: Number of rows per page (default: 1000, Supabase max)
        max_retries: Max retry attempts per page (default: 3)

    Returns:
        List of all session rows from the table

    Raises:
        SupabaseQueryError: If any page fetch fails after retries
    """
    all_rows: list[SessionRawRow] = []
    offset = 0
    page_number = 1

    while True:
        logger.debug(f"Fetching page {page_number} (offset: {offset})")

        rows = _fetch_page_with_retry(
            client=client,
            table_name="sessions_raw",
            offset=offset,
            page_size=page_size,
            max_retries=max_retries,
        )

        all_rows.extend(rows)
        logger.debug(f"Page {page_number}: fetched {len(rows)} rows (total: {len(all_rows)})")

        # If we got fewer rows than page_size, we've reached the end
        if len(rows) < page_size:
            break

        offset += page_size
        page_number += 1

    return all_rows


def compute_metrics_for_employees(
    sessions: list[SessionRawRow],
    now_utc: datetime,
) -> list[SessionMetricsRow]:
    """
    Compute aggregated metrics for each employee from session data.

    Metrics computed:
    - completed_count: Number of sessions with status "completed"
    - cancelled_count: Number of sessions with status "cancelled"
    - days_since_last_completed: Days since most recent completed session's end_at

    Note: Employees with only "scheduled" sessions are not included in output.

    Args:
        sessions: List of session rows from sessions_raw table
        now_utc: Current UTC time for calculating days_since

    Returns:
        List of computed metrics, one per employee
    """
    # Aggregate data by employee
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

            # Track the most recent completed session's end time
            end_at = parse_iso_datetime(session.get("end_at"))
            if end_at:
                current_max = employee_data[emp_id]["max_completed_end_at"]
                if current_max is None or end_at > current_max:
                    employee_data[emp_id]["max_completed_end_at"] = end_at

        elif status == "cancelled":
            employee_data[emp_id]["cancelled_count"] += 1

    # Build output metrics list
    computed_at_str = now_utc.isoformat()
    metrics: list[SessionMetricsRow] = []

    for emp_id, data in employee_data.items():
        # Calculate days since last completed session
        days_since: int | None = None
        max_end = data["max_completed_end_at"]

        if max_end is not None:
            delta = now_utc - max_end
            days_since = max(0, delta.days)  # Ensure non-negative

        metrics.append({
            "employee_id": emp_id,
            "completed_count": data["completed_count"],
            "cancelled_count": data["cancelled_count"],
            "days_since_last_completed": days_since,
            "computed_at": computed_at_str,
        })

    return metrics


def upsert_session_metrics(
    client: Client,
    metrics: list[SessionMetricsRow],
    max_retries: int = 3,
    base_delay: float = 1.0,
) -> None:
    """
    Upsert computed metrics into session_metrics table.

    Uses employee_id as the conflict key - existing rows are updated,
    new employee_ids are inserted.

    Args:
        client: Supabase client instance
        metrics: List of metrics to upsert
        max_retries: Max retry attempts (default: 3)
        base_delay: Base delay for exponential backoff (default: 1.0)

    Raises:
        SupabaseQueryError: If upsert fails after all retries
    """
    if not metrics:
        logger.debug("No metrics to upsert, skipping")
        return

    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            response = client.table("session_metrics").upsert(
                metrics,
                on_conflict="employee_id",
            ).execute()

            if response.data is None:
                raise SupabaseQueryError("Failed to upsert session_metrics: response.data is None")

            return  # Success

        except (ConnectError, TimeoutException) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                logger.warning(
                    f"Upsert attempt {attempt + 1}/{max_retries} failed: {e}. "
                    f"Retrying in {delay}s..."
                )
                time.sleep(delay)
            else:
                logger.error(f"All {max_retries} upsert attempts failed")

        except Exception as e:
            logger.error(f"Non-retryable error upserting metrics: {e}")
            raise SupabaseQueryError(f"Failed to upsert session_metrics: {e}") from e

    raise SupabaseQueryError(
        f"Failed to upsert session_metrics after {max_retries} attempts"
    ) from last_exception


def run_session_metrics_pipeline(client: Client) -> int:
    """
    Main entry point: fetch sessions, compute metrics, upsert results.

    Orchestrates the full pipeline:
    1. Fetch all sessions from sessions_raw (with pagination & retry)
    2. Compute per-employee metrics
    3. Upsert metrics to session_metrics table

    Args:
        client: Supabase client instance

    Returns:
        Number of employees processed

    Raises:
        SupabaseQueryError: If any database operation fails
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
