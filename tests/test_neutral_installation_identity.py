from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = (ROOT / "beta_launcher.py").read_text(encoding="utf-8")
INSTALLER = (ROOT / "installer" / "WealthOSBeta.iss").read_text(encoding="utf-8")


def test_internal_uuid_is_registry_backed_and_never_enters_url_or_auth():
    assert "uuid.uuid4()" in LAUNCHER
    assert 'REGISTRY_VALUE = "InstallationId"' in LAUNCHER
    assert "parsed.version != 4" in LAUNCHER
    assert "parsed.variant != uuid.RFC_4122" in LAUNCHER
    assert "?tester=" not in LAUNCHER
    assert "BetaIdPage" not in INSTALLER


def test_missing_locator_with_existing_instance_fails_closed():
    assert "while managed instances exist" in LAUNCHER
    assert "any(instances_root.iterdir())" in LAUNCHER


def test_missing_or_invalid_locator_has_a_graceful_bilingual_fail_closed_dialog():
    assert "class InstallationLocatorError" in LAUNCHER
    assert "show_locator_recovery_message()" in LAUNCHER
    assert "لم يتم حذف أو تعديل أي بيانات" in LAUNCHER
    assert "No data was deleted or changed" in LAUNCHER
    assert "Do not create a" in LAUNCHER
    assert "new instance or move data folders manually" in LAUNCHER
    assert "MessageBoxW" in LAUNCHER
    assert "raise SystemExit(2) from None" in LAUNCHER


def test_locator_recovery_does_not_offer_automatic_instance_adoption():
    recovery_block = LAUNCHER.split("def show_locator_recovery_message", 1)[1].split(
        "def resolve_application_root", 1
    )[0]
    assert "uuid.uuid4" not in recovery_block
    assert "SetValueEx" not in recovery_block
    assert "rmtree" not in recovery_block


def test_instance_paths_are_contained_and_reparse_checked():
    assert 'application_root / "instances"' in LAUNCHER
    assert "is_reparse_point(instances_root)" in LAUNCHER
    assert "is_reparse_point(candidate)" in LAUNCHER
    assert "resolved.parent != instances_root" in LAUNCHER
