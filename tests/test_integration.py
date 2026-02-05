"""
Integration tests using real Supabase API.

These tests fetch actual data from the database to verify data structure
and pipeline functionality. If the schema changes, tests will fail,
allowing quick detection of breaking changes.
"""
import pytest

from app.compute_session_metrics import (
    fetch_all_sessions,
    compute_metrics_for_employees,
    run_session_metrics_pipeline,
)
from app.datetime_utils import utc_now


class TestFetchAllSessions:
    """
    Tests for fetching data from sessions_raw table.

    Verifies that Supabase API calls work correctly and
    returned data structure matches expectations.
    """

    def test_fetch_returns_list(self, supabase_client):
        """Verify return type is a list."""
        sessions = fetch_all_sessions(supabase_client)
        assert isinstance(sessions, list)

    def test_fetch_returns_data(self, supabase_client):
        """Verify database contains at least one record."""
        sessions = fetch_all_sessions(supabase_client)
        assert len(sessions) > 0, "Expected at least one session in database"

    def test_session_has_required_fields(self, supabase_client):
        """
        Verify each session contains all required fields.

        This test fails if Supabase schema changes and a field is removed.
        """
        sessions = fetch_all_sessions(supabase_client)
        required_fields = ["session_id", "employee_id", "status", "start_at"]

        for session in sessions:
            for field in required_fields:
                assert field in session, f"Missing required field: {field}"

    def test_session_field_types(self, supabase_client):
        """
        Verify each field has the correct data type.

        - session_id, employee_id, status, start_at: string
        - end_at: string or None (can be None for non-completed sessions)
        """
        sessions = fetch_all_sessions(supabase_client)

        for session in sessions:
            assert isinstance(session["session_id"], str)
            assert isinstance(session["employee_id"], str)
            assert isinstance(session["status"], str)
            assert isinstance(session["start_at"], str)
            assert session["end_at"] is None or isinstance(session["end_at"], str)

    def test_status_values_are_valid(self, supabase_client):
        """
        Verify status field contains only allowed values.

        Unexpected status values could break business logic,
        so this test validates data quality.
        """
        sessions = fetch_all_sessions(supabase_client)
        valid_statuses = {"completed", "cancelled", "scheduled"}

        for session in sessions:
            assert session["status"] in valid_statuses, (
                f"Unexpected status: {session['status']}"
            )


class TestComputeMetrics:
    """
    Tests for metrics computation.

    Verifies that compute_metrics_for_employees function
    returns correct results using real API data.
    """

    def test_compute_returns_list(self, supabase_client):
        """Verify return type is a list."""
        sessions = fetch_all_sessions(supabase_client)
        now = utc_now()
        metrics = compute_metrics_for_employees(sessions, now)

        assert isinstance(metrics, list)

    def test_metrics_has_required_fields(self, supabase_client):
        """
        Verify computed metrics contain all required fields.

        These fields are required for upserting to session_metrics table.
        """
        sessions = fetch_all_sessions(supabase_client)
        now = utc_now()
        metrics = compute_metrics_for_employees(sessions, now)

        required_fields = [
            "employee_id",
            "completed_count",
            "cancelled_count",
            "days_since_last_completed",
            "computed_at",
        ]

        for metric in metrics:
            for field in required_fields:
                assert field in metric, f"Missing required field: {field}"

    def test_counts_are_non_negative(self, supabase_client):
        """
        Verify completed_count and cancelled_count are non-negative integers.

        Negative counts are logically impossible and indicate a bug.
        """
        sessions = fetch_all_sessions(supabase_client)
        now = utc_now()
        metrics = compute_metrics_for_employees(sessions, now)

        for metric in metrics:
            assert metric["completed_count"] >= 0
            assert metric["cancelled_count"] >= 0
            assert isinstance(metric["completed_count"], int)
            assert isinstance(metric["cancelled_count"], int)

    def test_days_since_is_valid(self, supabase_client):
        """
        Verify days_since_last_completed is None or a non-negative integer.

        - None: employee has no completed sessions
        - >= 0: days elapsed since last completed session
        """
        sessions = fetch_all_sessions(supabase_client)
        now = utc_now()
        metrics = compute_metrics_for_employees(sessions, now)

        for metric in metrics:
            days = metric["days_since_last_completed"]
            if days is not None:
                assert isinstance(days, int)
                assert days >= 0


class TestPipeline:
    """
    Tests for the full pipeline.

    Verifies that fetch -> compute -> upsert flow completes without errors.
    """

    def test_pipeline_runs_successfully(self, supabase_client):
        """Verify pipeline completes without raising exceptions."""
        employee_count = run_session_metrics_pipeline(supabase_client)
        assert isinstance(employee_count, int)
        assert employee_count >= 0

    def test_pipeline_returns_correct_count(self, supabase_client):
        """
        Verify pipeline returns the correct employee count.

        Only employees with completed or cancelled sessions are counted.
        Employees with only scheduled sessions are not included.
        """
        sessions = fetch_all_sessions(supabase_client)

        # Count unique employees with completed or cancelled status
        employees_with_metrics = set()
        for s in sessions:
            if s["status"] in ("completed", "cancelled"):
                employees_with_metrics.add(s["employee_id"])

        employee_count = run_session_metrics_pipeline(supabase_client)
        assert employee_count == len(employees_with_metrics)
