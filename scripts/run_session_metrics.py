"""
CLI runner for session metrics computation.

Usage:
    python -m scripts.run_session_metrics
    python -m scripts.run_session_metrics --debug
"""
import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from app.logger import setup_logger
from app.supabase_client import get_supabase_client, SupabaseConfigError
from app.compute_session_metrics import run_session_metrics_pipeline, SupabaseQueryError


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute and upsert session metrics")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging"
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = setup_logger("app", level=log_level)

    try:
        client = get_supabase_client()
        employee_count = run_session_metrics_pipeline(client)
        logger.info(f"Successfully processed metrics for {employee_count} employee(s)")
        return 0

    except SupabaseConfigError as e:
        logger.error(f"Configuration error: {e}")
        return 1

    except SupabaseQueryError as e:
        logger.error(f"Database error: {e}")
        return 1

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
