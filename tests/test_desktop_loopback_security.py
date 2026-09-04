import asyncio
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

from main import security_controls


ORIGIN = "http://127.0.0.1:49152"
CAPABILITY = "c" * 64


def request(path="/api/v1/account/me", method="GET", headers=()):
    app = SimpleNamespace(
        state=SimpleNamespace(
            desktop_origin=ORIGIN,
            launch_capability=CAPABILITY,
            bootstrap_path=f"/desktop-bootstrap/{CAPABILITY}",
        )
    )
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "query_string": b"",
            "headers": [(key.lower().encode(), value.encode()) for key, value in headers],
            "client": ("127.0.0.1", 50000),
            "server": ("127.0.0.1", 49152),
            "scheme": "http",
            "app": app,
        }
    )


async def allowed(_request):
    return Response("ok")


def run(value):
    return asyncio.run(value)


def test_readiness_is_the_only_capability_free_endpoint():
    health = run(security_controls(request("/health", headers=(("host", "127.0.0.1:49152"),)), allowed))
    missing = run(security_controls(request(headers=(("host", "127.0.0.1:49152"),)), allowed))
    assert health.status_code == 200
    assert missing.status_code == 401


def test_bootstrap_sets_httponly_strict_capability_cookie():
    response = run(security_controls(request(f"/desktop-bootstrap/{CAPABILITY}", headers=(("host", "127.0.0.1:49152"),)), allowed))
    cookie = response.headers["set-cookie"].lower()
    assert response.status_code == 303
    assert "httponly" in cookie and "samesite=strict" in cookie


def test_host_proxy_and_cross_origin_state_changes_fail_closed():
    bad_host = run(security_controls(request(headers=(("host", "evil.invalid"),)), allowed))
    proxy = run(security_controls(request(headers=(("host", "127.0.0.1:49152"),("x-forwarded-host","evil.invalid"))), allowed))
    bad_origin = run(security_controls(request(method="POST", headers=(("host", "127.0.0.1:49152"),("cookie",f"wealthos_launch={CAPABILITY}"),("origin","https://evil.invalid"),("sec-fetch-site","cross-site"))), allowed))
    assert bad_host.status_code == 400
    assert proxy.status_code == 400
    assert bad_origin.status_code == 403


def test_exact_origin_capability_request_is_allowed():
    response = run(security_controls(request(path="/local-test", method="POST", headers=(("host", "127.0.0.1:49152"),("cookie",f"wealthos_launch={CAPABILITY}"),("origin",ORIGIN),("sec-fetch-site","same-origin"))), allowed))
    assert response.status_code == 200
