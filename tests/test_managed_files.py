from scripts.managed_files import register_managed_file


def test_registry_records_only_exact_owned_files_and_preserves_unknown(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.managed_files.load_hmac_key", lambda: b"k" * 32)
    root = tmp_path / "instance"
    for child in ("backups", "diagnostics", "state"):
        (root / child).mkdir(parents=True)
    owned = root / "backups" / "owned.db"
    unknown = root / "backups" / "external-sentinel.txt"
    owned.write_bytes(b"owned")
    unknown.write_bytes(b"unknown")

    register_managed_file(root, owned)

    registry = root / "state" / "managed-files-v1.txt"
    assert "backups\\owned.db" in registry.read_text(encoding="utf-8")
    assert "hmac-sha256=" in registry.read_text(encoding="utf-8")
    assert unknown.read_bytes() == b"unknown"


def test_registry_rejects_files_outside_owned_prefixes(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.managed_files.load_hmac_key", lambda: b"k" * 32)
    root = tmp_path / "instance"
    (root / "state").mkdir(parents=True)
    outside = root / "unknown.txt"
    outside.write_text("unknown", encoding="utf-8")

    try:
        register_managed_file(root, outside)
    except RuntimeError as error:
        assert "outside the versioned ownership registry" in str(error)
    else:
        raise AssertionError("unowned path was registered")
