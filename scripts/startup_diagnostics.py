import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Type

from scripts.managed_files import register_managed_file


KNOWN_MESSAGES = {
    "Both legacy and canonical WealthOS databases contain a legacy database with financial activity. Automatic merge is disabled; preserve both files and request recovery review.": "Two databases require recovery review because the legacy database contains financial activity.",
    "A coexisting WealthOS database failed its integrity check.": "A coexisting database failed its integrity check.",
    "A coexisting WealthOS database has foreign-key violations.": "A coexisting database has foreign-key violations.",
    "A coexisting WealthOS database path is unsafe.": "A coexisting database path did not pass safety validation.",
}


def write_startup_failure(
    diagnostics_root: Path,
    stage: str,
    exception_type: Type[BaseException],
    exception: BaseException,
) -> Path | None:
    """Write a minimal local diagnostic without paths, tracebacks, or user data."""
    try:
        diagnostics_root.mkdir(exist_ok=True)
        timestamp = datetime.now(timezone.utc)
        payload = {
            "application": "WealthOS",
            "version": "0.1.0",
            "timestamp_utc": timestamp.isoformat(),
            "stage": stage,
            "error_type": exception_type.__name__,
            "message": KNOWN_MESSAGES.get(str(exception), "WealthOS could not complete local startup."),
        }
        destination = diagnostics_root / f"startup-failure-{timestamp:%Y%m%dT%H%M%SZ}.json"
        temporary = diagnostics_root / f".{destination.name}.{os.getpid()}.tmp"
        temporary.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, destination)
        register_managed_file(diagnostics_root.parent, destination)
        return destination
    except OSError:
        return None
