import time
from collections.abc import Callable
from urllib.error import URLError
from urllib.request import urlopen


def wait_for_http_health(
    url: str,
    *,
    timeout_seconds: float = 90.0,
    poll_seconds: float = 0.25,
    request_timeout_seconds: float = 1.0,
    opener: Callable = urlopen,
    monotonic: Callable[[], float] = time.monotonic,
    sleeper: Callable[[float], None] = time.sleep,
) -> bool:
    """Wait for a local HTTP health endpoint without affecting server startup."""
    deadline = monotonic() + timeout_seconds
    while True:
        remaining = deadline - monotonic()
        if remaining <= 0:
            return False
        try:
            with opener(url, timeout=min(request_timeout_seconds, remaining)) as response:
                if getattr(response, "status", None) == 200:
                    return True
        except (OSError, TimeoutError, URLError):
            pass
        remaining = deadline - monotonic()
        if remaining <= 0:
            return False
        sleeper(min(poll_seconds, remaining))
