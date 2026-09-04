from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_hosted_auth_gate_precedes_local_setup_gate():
    router = (ROOT / "frontend/src/AppRouter.tsx").read_text(encoding="utf-8")
    gate = (ROOT / "frontend/src/components/BootstrapGate.tsx").read_text(encoding="utf-8")
    assert "<BootstrapGate>" in router
    assert "<SetupGate>" not in router
    assert "fetch(`${API}/account/me`" in gate
    assert "response.status === 401" in gate
    assert "setMode('auth')" in gate
    assert "response.status === 423" in gate
    assert "<SetupGate>{children}</SetupGate>" in gate


def test_frontend_sends_session_csrf_token_for_mutations():
    api = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
    assert "__Host-wealthos-csrf=" in api
    assert "'X-CSRF-Token'" in api
    assert "credentials: 'same-origin'" in api


def test_authenticated_refresh_bypasses_local_setup_wizard():
    gate = (ROOT / "frontend/src/components/SetupGate.tsx").read_text(encoding="utf-8")
    profile_probe = gate.index("getAccountProfile().then")
    setup_probe = gate.index("getSetupStatus().then", profile_probe)
    assert profile_probe < setup_probe
    assert "setWebAuthenticated(true)" in gate[profile_probe:setup_probe]
