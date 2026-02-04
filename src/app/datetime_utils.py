from datetime import datetime, timezone


def parse_iso_datetime(value: str | None) -> datetime | None:
    """Parse ISO 8601 datetime string to timezone-aware datetime in UTC."""
    if value is None:
        return None

    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return ensure_utc(dt)


def ensure_utc(dt: datetime | None) -> datetime | None:
    """Convert datetime to UTC. Raises if datetime is naive."""
    if dt is None:
        return None

    if dt.tzinfo is None:
        raise ValueError("Naive datetime not allowed; use timezone-aware datetime")

    return dt.astimezone(timezone.utc)


def utc_now() -> datetime:
    """Return current time in UTC."""
    return datetime.now(timezone.utc)
