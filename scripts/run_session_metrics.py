"""
CLI runner for session metrics computation.

Usage:
    python -m scripts.run_session_metrics
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.supabase_client import get_supabase_client, SupabaseConfigError
from app.compute_session_metrics import run_session_metrics_pipeline, SupabaseQueryError


def main() -> int:
    try:
        client = get_supabase_client()
        employee_count = run_session_metrics_pipeline(client, debug=True)
        print(f"Successfully processed metrics for {employee_count} employee(s).")
        return 0

    except SupabaseConfigError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1

    except SupabaseQueryError as e:
        print(f"Database error: {e}", file=sys.stderr)
        return 1

    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
