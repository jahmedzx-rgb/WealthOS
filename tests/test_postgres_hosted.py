"""Opt-in smoke test against a freshly migrated, disposable local PostgreSQL."""

import os
from urllib.parse import urlsplit

import pytest


@pytest.mark.skipif(os.getenv("RUN_DISPOSABLE_POSTGRES_TEST") != "1", reason="Requires disposable PostgreSQL")
def test_migrated_postgres_registration_sessions_and_isolation():
    url = urlsplit(os.environ["DATABASE_URL"])
    assert url.hostname == "127.0.0.1" and url.path == "/codex_railway_beta_test"
    assert url.port == 55440 and url.username == "codex_beta_test"
    from fastapi.testclient import TestClient
    from sqlalchemy import text
    import main
    from app.database.engine import SessionLocal
    from app.security.web_auth import CSRF_COOKIE

    anonymous = TestClient(main.app, base_url="https://testserver")
    assert anonymous.get("/ready").status_code == 200
    assert anonymous.get("/api/v1/account/me").status_code == 401
    invites = os.environ["WEB_INVITE_CODES"].split(",")
    clients = []
    for number in range(2):
        client = TestClient(main.app, base_url="https://testserver")
        response = client.post("/api/v1/auth/register", json={
            "username": f"SmokeUser{number}", "password": "Synthetic-smoke-password-123",
            "locale": "en", "invite_code": invites[number],
        })
        assert response.status_code == 201, response.text
        assert "Secure" in response.headers.get("set-cookie", "")
        assert client.get("/api/v1/account/me").status_code == 200
        clients.append(client)
    reused = anonymous.post("/api/v1/auth/register", json={
        "username": "ReusedInvite", "password": "Synthetic-smoke-password-123",
        "locale": "en", "invite_code": invites[0],
    })
    assert reused.status_code == 403
    with SessionLocal() as database:
        assert database.execute(text("SELECT COUNT(*) FROM currencies WHERE code IN ('SAR', 'USD')")).scalar_one() == 2
        assert database.execute(text("SELECT COUNT(*) FROM accounts WHERE code IN (1110, 1120)")).scalar_one() == 2
        assert database.execute(text("SELECT COUNT(*) FROM portfolio_strategies")).scalar_one() == 5
        assert database.execute(text("SELECT COUNT(*) FROM portfolio_objectives")).scalar_one() == 5
        assert database.execute(text("SELECT COUNT(*) FROM portfolios")).scalar_one() == 0
        assert database.execute(text("SELECT COUNT(*) FROM journal_entries")).scalar_one() == 0
        assert database.execute(text("SELECT COUNT(*) FROM web_invite_codes")).scalar_one() == 10
        assert database.execute(text("SELECT COUNT(*) FROM web_registration_slots")).scalar_one() == 2
        assert database.execute(text("SELECT COUNT(*) FROM users WHERE username = 'ReusedInvite'")).scalar_one() == 0
    a, b = clients
    b_csrf = b.cookies.get(CSRF_COOKIE)
    response = b.post("/api/v1/imports/batches", headers={"x-csrf-token": b_csrf}, json={
        "filename": "synthetic-only.pdf", "file_size": 128, "file_type": "application/pdf",
        "operations": [{"operation_type": "expense", "description": "PRIVATE-SYNTHETIC-MARKER",
                        "amount": "42.00", "currency": "SAR", "confidence": 90,
                        "source_text": "PRIVATE-SYNTHETIC-MARKER"}],
    })
    assert response.status_code == 200, response.text
    batch = response.json()
    assert "PRIVATE-SYNTHETIC-MARKER" not in a.get("/api/v1/account/backup").text
    assert a.delete(f"/api/v1/imports/batches/{batch['id']}", headers={"x-csrf-token": a.cookies.get(CSRF_COOKIE)}).status_code == 404
    assert a.post("/api/v1/auth/logout").status_code == 403
    assert a.post("/api/v1/auth/logout", headers={"x-csrf-token": a.cookies.get(CSRF_COOKIE)}).status_code == 200
    assert a.get("/api/v1/account/me").status_code == 401
    restarted = TestClient(main.app, base_url="https://testserver")
    restarted.cookies.update(b.cookies)
    assert restarted.get("/api/v1/account/me").status_code == 200
