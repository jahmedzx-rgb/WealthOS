from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import main as main_module
from app.core.models import Currency, Entity, User
from app.core.settings import settings
from app.database.base import Base
from app.database.engine import get_db
from app.security.models import WebInviteCode, WebSessionRecord
from app.security.web_auth import CSRF_COOKIE, SESSION_COOKIE, token_digest


def seed_invites(session_factory, *codes: str) -> None:
    with session_factory() as db:
        db.add_all(WebInviteCode(code_hash=token_digest(code)) for code in codes)
        db.commit()


def test_two_web_accounts_are_authenticated_and_export_isolated(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'web-auth.sqlite3'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_db():
        db = testing_session()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(settings, "WEB_MODE", True)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(main_module, "SessionLocal", testing_session)
    main_module.app.dependency_overrides[get_db] = override_db
    seed_invites(testing_session, "invite-alice-0001", "invite-bob-0000002")
    try:
        anonymous = TestClient(main_module.app)
        assert anonymous.get("/api/v1/account/me").status_code == 401

        a = TestClient(main_module.app)
        b = TestClient(main_module.app)
        first = a.post("/api/v1/auth/register", json={"username": "Alice", "password": "A-strong-passphrase-123", "locale": "en", "invite_code": "invite-alice-0001"})
        second = b.post("/api/v1/auth/register", json={"username": "Bob", "password": "B-strong-passphrase-456", "locale": "ar", "invite_code": "invite-bob-0000002"})
        assert first.status_code == 201
        assert second.status_code == 201
        assert a.get("/api/v1/account/me").json()["username"] == "Alice"
        assert b.get("/api/v1/account/me").json()["locale"] == "ar"

        with testing_session() as db:
            currency = Currency(code="SAR", name="Saudi Riyal", symbol="SAR")
            db.add(currency)
            db.flush()
            db.add(Entity(user_id=second.json()["id"], code="BOB-PRIVATE", name="BOB-PRIVATE-MARKER", entity_type="PERSON", base_currency_id=currency.id))
            db.commit()

        exported = a.get("/api/v1/account/backup")
        assert exported.status_code == 200
        assert "BOB-PRIVATE-MARKER" not in exported.text

        b_csrf = b.cookies.get(CSRF_COOKIE)
        batch = b.post("/api/v1/imports/batches", headers={"x-csrf-token": b_csrf}, json={
            "filename": "bob-private.pdf", "file_size": 128, "file_type": "application/pdf",
            "operations": [{"operation_type": "expense", "description": "BOB-FILE-MARKER",
                            "amount": "42.00", "currency": "SAR", "confidence": 90,
                            "source_text": "BOB-FILE-MARKER"}],
        })
        assert batch.status_code == 200
        batch_id = batch.json()["id"]
        operation_id = batch.json()["operations"][0]["id"]
        a_csrf = a.cookies.get(CSRF_COOKIE)
        assert a.patch(f"/api/v1/imports/operations/{operation_id}/IGNORED", headers={"x-csrf-token": a_csrf}).status_code == 404
        assert a.delete(f"/api/v1/imports/batches/{batch_id}", headers={"x-csrf-token": a_csrf}).status_code == 404
        assert any(item["id"] == batch_id for item in b.get("/api/v1/imports/batches").json())

        with testing_session() as db:
            alice = db.get(User, first.json()["id"])
            assert alice.password_hash.startswith("$argon2id$")

        assert a.post("/api/v1/auth/logout").status_code == 403
        csrf = a.cookies.get(CSRF_COOKIE)
        assert csrf
        assert a.post("/api/v1/auth/logout", headers={"x-csrf-token": csrf}).status_code == 200
        assert a.get("/api/v1/account/me").status_code == 401
        assert b.get("/api/v1/account/me").status_code == 200

        restarted_worker = TestClient(main_module.app)
        restarted_worker.cookies.update(b.cookies)
        assert restarted_worker.get("/api/v1/account/me").status_code == 200

        a_login = a.post("/api/v1/auth/login", json={"username": "Alice", "password": "A-strong-passphrase-123", "locale": "ar"})
        assert a_login.status_code == 200
        assert a.get("/api/v1/account/me").json()["locale"] == "en"
        second_a = TestClient(main_module.app)
        assert second_a.post("/api/v1/auth/login", json={"username": "Alice", "password": "A-strong-passphrase-123"}).status_code == 200
        a_csrf = a.cookies.get(CSRF_COOKIE)
        assert a.post("/api/v1/auth/logout-all", headers={"x-csrf-token": a_csrf}).status_code == 200
        assert second_a.get("/api/v1/account/me").status_code == 401

        for _ in range(10):
            failed = anonymous.post("/api/v1/auth/login", json={"username": "Nobody", "password": "not-the-right-password"})
            assert failed.status_code == 401
        assert anonymous.post("/api/v1/auth/login", json={"username": "Nobody", "password": "not-the-right-password"}).status_code == 429

        with testing_session() as db:
            b_session = db.get(WebSessionRecord, token_digest(b.cookies.get(SESSION_COOKIE)))
            b_session.expires_at = b_session.expires_at.replace(year=2000)
            db.commit()
        assert b.get("/api/v1/account/me").status_code == 401
    finally:
        main_module.app.dependency_overrides.clear()


def test_username_normalization_is_unique(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'username.sqlite3'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    testing_session = sessionmaker(bind=engine)

    def override_db():
        with testing_session() as db:
            yield db

    monkeypatch.setattr(settings, "WEB_MODE", True)
    monkeypatch.setattr(settings, "COOKIE_SECURE", False)
    monkeypatch.setattr(main_module, "SessionLocal", testing_session)
    main_module.app.dependency_overrides[get_db] = override_db
    seed_invites(testing_session, "invite-case-00001", "invite-case-00002")
    try:
        first = TestClient(main_module.app).post("/api/v1/auth/register", json={"username": "CaseUser", "password": "A-strong-passphrase-123", "locale": "en", "invite_code": "invite-case-00001"})
        duplicate = TestClient(main_module.app).post("/api/v1/auth/register", json={"username": "caseuser", "password": "B-strong-passphrase-456", "locale": "en", "invite_code": "invite-case-00002"})
        assert first.status_code == 201
        assert duplicate.status_code == 409
        assert duplicate.json()["detail"]["key"] == "auth.username_taken"
    finally:
        main_module.app.dependency_overrides.clear()
