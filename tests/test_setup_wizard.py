from decimal import Decimal

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request
from types import SimpleNamespace

import app.database.model_registry  # noqa: F401
from app.api.v1.account import PasswordChangeRequest, PasswordDisableRequest, RecoveryRequest, SetupCompleteRequest, _password_matches, change_password, complete_setup, current_user, disable_password, lock, recover, setup_status, unlock, UnlockRequest
from app.security.local_lock import session_token_hash
from fastapi.responses import JSONResponse
import json
from app.core.models.user import User
from app.database.base import Base


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    user = User(
        id=1,
        email="ahmed@local.wealthos",
        full_name="Ahmed",
        investor_type="INDIVIDUAL",
        default_dividend_withholding_tax_rate=Decimal("0"),
    )
    session.add(user)
    session.commit()
    return session, user


def request(**changes):
    values = dict(
        full_name="DonAhmed",
        email="don@example.com",
        local_password="safe-local-password",
        preferred_language="ar",
        base_currency_code="SAR",
        enabled_currency_codes=["SAR", "USD"],
        nationality="Saudi Arabian",
        country_of_residence="Saudi Arabia",
        tax_residence="Saudi Arabia",
        investor_type="INDIVIDUAL",
        local_data_acknowledged=True,
        existing_data_choice=None,
    )
    values.update(changes)
    return SetupCompleteRequest(**values)


def http_request(legacy_candidates=0):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "app": SimpleNamespace(state=SimpleNamespace(legacy_candidate_count=legacy_candidates))})


def cookie_request(token: str, state):
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [(b"cookie", f"wealthos_unlock={token}".encode())], "app": SimpleNamespace(state=state)})


def result_body(result):
    return json.loads(result.body) if isinstance(result, JSONResponse) else result


def test_dashboard_setup_state_starts_incomplete_and_persists_backend_profile():
    db, user = make_session()
    assert setup_status(http_request(), user, db)["completed"] is False
    result = result_body(complete_setup(request(), http_request(), user, db))
    assert result["completed"] is True
    db.refresh(user)
    assert user.setup_completed is True
    assert user.full_name == "DonAhmed"
    assert user.preferred_language == "ar"
    assert user.enabled_currency_codes == ["SAR", "USD"]
    assert user.password_hash.startswith("$argon2id$v=19$m=65536,t=3,p=4$")
    assert result["recovery_code"]


def test_local_data_acknowledgement_is_mandatory():
    db, user = make_session()
    with pytest.raises(HTTPException) as error:
        complete_setup(request(local_data_acknowledged=False), http_request(), user, db)
    assert error.value.status_code == 400
    assert user.setup_completed is False


def test_existing_data_requires_explicit_resume(monkeypatch):
    db, user = make_session()
    monkeypatch.setattr("app.api.v1.account._has_existing_financial_data", lambda *_args: True)
    with pytest.raises(HTTPException) as error:
        complete_setup(request(existing_data_choice="REVIEW_MIGRATION"), http_request(), user, db)
    assert error.value.status_code == 409
    assert user.setup_completed is False
    result = result_body(complete_setup(request(existing_data_choice="RESUME_EXISTING"), http_request(), user, db))
    assert result["completed"] is True


def test_server_user_dependency_blocks_financial_api_before_setup():
    db, user = make_session()
    with pytest.raises(HTTPException) as error:
        current_user(user)
    assert error.value.status_code == 423
    user.setup_completed = True
    assert current_user(user) is user


def test_optional_password_is_a_real_unlock_credential():
    db, user = make_session()
    complete_setup(request(), http_request(), user, db)
    assert _password_matches("safe-local-password", user.password_hash)
    assert not _password_matches("wrong-password", user.password_hash)


def test_legacy_candidate_requires_explicit_clean_or_review_choice():
    db, user = make_session()
    with pytest.raises(HTTPException) as error:
        complete_setup(request(existing_data_choice="REVIEW_MIGRATION"), http_request(1), user, db)
    assert error.value.status_code == 409
    assert user.setup_completed is False
    assert result_body(complete_setup(request(existing_data_choice="START_CLEAN"), http_request(1), user, db))["completed"] is True


def test_setup_is_one_shot():
    db, user = make_session()
    complete_setup(request(), http_request(), user, db)
    with pytest.raises(HTTPException) as error:
        complete_setup(request(), http_request(), user, db)
    assert error.value.status_code == 409


def test_unlock_cookie_is_process_session_only_and_argon_rehashes(monkeypatch):
    db, user = make_session()
    response = complete_setup(request(), http_request(), user, db)
    cookie = response.headers["set-cookie"]
    assert "Max-Age" not in cookie and "Expires" not in cookie
    monkeypatch.setattr("app.api.v1.account.needs_rehash", lambda _encoded: True)
    old_hash = user.password_hash
    unlock(UnlockRequest(local_password="safe-local-password"), http_request(), user, db)
    assert user.password_hash != old_hash


def test_recovery_throttle_is_persisted_and_non_enumerating():
    db, user = make_session()
    complete_setup(request(), http_request(), user, db)
    payload = RecoveryRequest(recovery_code="A" * 32, new_local_password="another-safe-password")
    for _ in range(5):
        with pytest.raises(HTTPException) as error:
            recover(payload, http_request(), user, db)
        assert error.value.status_code == 401
        assert error.value.detail == "Recovery could not be completed."
    db.expire_all()
    persisted = db.get(User, user.id)
    assert persisted.failed_recovery_attempts == 5
    assert persisted.next_recovery_allowed_at is not None


def test_explicit_lock_revokes_stale_page_session():
    db, user = make_session()
    setup_request = http_request()
    response = complete_setup(request(), setup_request, user, db)
    token = response.headers["set-cookie"].split("wealthos_unlock=", 1)[1].split(";", 1)[0]
    state = setup_request.app.state
    assert session_token_hash(token) in state.unlock_sessions
    lock(cookie_request(token, state))
    assert session_token_hash(token) not in state.unlock_sessions


def test_password_change_rotates_recovery_and_disable_removes_password():
    db, user = make_session()
    setup_request = http_request()
    response = complete_setup(request(), setup_request, user, db)
    token = response.headers["set-cookie"].split("wealthos_unlock=", 1)[1].split(";", 1)[0]
    state = setup_request.app.state
    changed = change_password(PasswordChangeRequest(current_local_password="safe-local-password", new_local_password="replacement-safe-password"), cookie_request(token, state), user, db)
    new_token = changed.headers["set-cookie"].split("wealthos_unlock=", 1)[1].split(";", 1)[0]
    assert _password_matches("replacement-safe-password", user.password_hash)
    assert not _password_matches("safe-local-password", user.password_hash)
    disabled = disable_password(PasswordDisableRequest(current_local_password="replacement-safe-password"), cookie_request(new_token, state), user, db)
    assert disabled.status_code == 200
    assert user.password_hash is None and user.recovery_code_hash is None


@pytest.mark.parametrize("operation", ["change", "disable"])
def test_sensitive_password_reverification_uses_persisted_lockout(operation):
    db, user = make_session()
    setup_request = http_request()
    response = complete_setup(request(), setup_request, user, db)
    token = response.headers["set-cookie"].split("wealthos_unlock=", 1)[1].split(";", 1)[0]
    state = setup_request.app.state
    for _ in range(5):
        with pytest.raises(HTTPException) as error:
            if operation == "change":
                change_password(PasswordChangeRequest(current_local_password="wrong-password", new_local_password="replacement-safe-password"), cookie_request(token, state), user, db)
            else:
                disable_password(PasswordDisableRequest(current_local_password="wrong-password"), cookie_request(token, state), user, db)
        assert error.value.status_code == 401
        assert error.value.detail == "Password verification is required."
    db.expire_all()
    persisted = db.get(User, user.id)
    assert persisted.failed_unlock_attempts == 5
    assert persisted.next_unlock_allowed_at is not None


@pytest.mark.parametrize("operation", ["change", "disable"])
def test_sensitive_password_reverification_success_resets_failures(operation):
    db, user = make_session()
    setup_request = http_request()
    response = complete_setup(request(), setup_request, user, db)
    token = response.headers["set-cookie"].split("wealthos_unlock=", 1)[1].split(";", 1)[0]
    state = setup_request.app.state
    user.failed_unlock_attempts = 4
    db.commit()
    if operation == "change":
        change_password(PasswordChangeRequest(current_local_password="safe-local-password", new_local_password="replacement-safe-password"), cookie_request(token, state), user, db)
    else:
        disable_password(PasswordDisableRequest(current_local_password="safe-local-password"), cookie_request(token, state), user, db)
    assert user.failed_unlock_attempts == 0
    assert user.next_unlock_allowed_at is None


def test_frontend_route_gate_blocks_dashboard_until_backend_setup_complete():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    router = (root / "frontend/src/AppRouter.tsx").read_text(encoding="utf-8")
    gate = (root / "frontend/src/components/SetupGate.tsx").read_text(encoding="utf-8")
    wizard = (root / "frontend/src/components/SetupWizard.tsx").read_text(encoding="utf-8")
    wizard_select = (root / "frontend/src/components/WizardSelect.tsx").read_text(encoding="utf-8")
    assert "<SetupGate>" in router
    assert "if(!status.completed)return <SetupWizard" in gate
    assert "RESUME_EXISTING" in wizard and "REVIEW_MIGRATION" in wizard
    assert "Search currencies" in wizard and "Search countries" in wizard
    assert "scrollIntoView({block:'nearest'})" in wizard_select
    assert "opensUp" not in wizard_select and "opens-up" not in wizard_select and "below<210&&above>below" not in wizard_select
    assert "wealthos-app-icon.svg" in wizard and "wealthos-app-icon.svg" in gate
    account = (root / "app/api/v1/account.py").read_text(encoding="utf-8")
    assert '_set_desktop_window_mode(request, "main" if user.setup_completed and unlocked else "compact")' in account
    assert 'request.headers' not in account[account.index("def _set_desktop_window_mode"):account.index("def _session_binding")]
    launcher = (root / "beta_launcher.py").read_text(encoding="utf-8")
    assert "adopt_beta_profile_database(" not in launcher


def test_official_brand_asset_is_shared_by_sidebar_and_favicon():
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    sidebar = (root / "frontend/src/components/layout/Sidebar.tsx").read_text(encoding="utf-8")
    sidebar_css = (root / "frontend/src/components/layout/Sidebar.css").read_text(encoding="utf-8")
    assert "wealthos-app-icon.svg" in sidebar and 'aria-hidden="true"' in sidebar
    assert ".sidebar__brand-mark img{display:block;width:36px;height:36px" in sidebar_css
    assert (root / "frontend/public/favicon.svg").read_bytes() == (root / "assets/branding/wealthos-app-icon.svg").read_bytes()
