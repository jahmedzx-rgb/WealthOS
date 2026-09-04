from urllib.error import URLError

from scripts.service_readiness import wait_for_http_health


class Response:
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


def test_health_poll_retries_until_service_is_ready():
    attempts = []

    def opener(_url, *, timeout):
        attempts.append(timeout)
        if len(attempts) < 3:
            raise URLError("not ready")
        return Response()

    assert wait_for_http_health(
        "http://127.0.0.1:8765/health",
        opener=opener,
        monotonic=lambda: 0.0,
        sleeper=lambda _seconds: None,
    )
    assert len(attempts) == 3


def test_health_poll_times_out_without_raising():
    clock = [0.0]

    def monotonic():
        return clock[0]

    def sleeper(seconds):
        clock[0] += seconds

    def opener(_url, *, timeout):
        clock[0] += timeout
        raise TimeoutError

    assert not wait_for_http_health(
        "http://127.0.0.1:8765/health",
        timeout_seconds=2.0,
        poll_seconds=0.25,
        request_timeout_seconds=0.5,
        opener=opener,
        monotonic=monotonic,
        sleeper=sleeper,
    )
    assert clock[0] == 2.0


def test_desktop_host_waits_for_health_before_window(tmp_path):
    host = (__import__("pathlib").Path(__file__).resolve().parents[1] / "scripts/desktop_host.py").read_text(encoding="utf-8")
    assert 'wait_for_http_health(f"{origin}/health"' in host
    assert "timeout_seconds=120.0" in host
    assert "time.sleep(1.2)" not in host
