import json

from scripts.startup_diagnostics import write_startup_failure


def test_startup_failure_diagnostic_is_local_and_redacted(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.managed_files.load_hmac_key", lambda: b"k" * 32)
    secret_path = r"C:\Users\Private\wealthos.db"
    diagnostics = tmp_path / "diagnostics"
    (tmp_path / "state").mkdir()
    result = write_startup_failure(
        diagnostics,
        "database-migration",
        RuntimeError,
        RuntimeError(f"failure at {secret_path}"),
    )

    assert result is not None
    payload = json.loads(result.read_text(encoding="utf-8"))
    assert payload["stage"] == "database-migration"
    assert payload["error_type"] == "RuntimeError"
    assert payload["message"] == "WealthOS could not complete local startup."
    assert secret_path not in result.read_text(encoding="utf-8")
