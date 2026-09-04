from pathlib import Path
import subprocess

import pytest

from scripts.managed_files import read_verified_registry, register_managed_file
from scripts.managed_wipe import wipe_managed_instance


def make_instance(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("scripts.managed_files.load_hmac_key", lambda: b"k" * 32)
    root = tmp_path / "instance"
    for child in ("data", "backups", "diagnostics", "state"):
        (root / child).mkdir(parents=True)
    (root / "data" / "wealthos.db").write_bytes(b"database")
    owned = root / "backups" / "owned.db"
    owned.write_bytes(b"owned")
    register_managed_file(root, owned)
    return root, owned


def test_unknown_sentinel_survives_and_causes_partial_failure(tmp_path, monkeypatch):
    root, owned = make_instance(tmp_path, monkeypatch)
    sentinel = root / "backups" / "unknown-sentinel.txt"
    sentinel.write_bytes(b"preserve")

    with pytest.raises(RuntimeError, match="Unknown files were preserved"):
        wipe_managed_instance(root, clear_locator=False)

    assert sentinel.read_bytes() == b"preserve"
    assert not owned.exists()
    assert (root / "state" / "managed-files-v1.txt").exists()


def test_registry_tamper_fails_before_deletion(tmp_path, monkeypatch):
    root, owned = make_instance(tmp_path, monkeypatch)
    registry = root / "state" / "managed-files-v1.txt"
    registry.write_text(registry.read_text(encoding="utf-8").replace("owned.db", "other.db"), encoding="utf-8")

    with pytest.raises(RuntimeError, match="integrity check failed"):
        wipe_managed_instance(root, clear_locator=False)

    assert owned.exists()
    assert (root / "data" / "wealthos.db").exists()


def test_injected_failure_keeps_registry_and_retry_is_idempotent(tmp_path, monkeypatch):
    root, _ = make_instance(tmp_path, monkeypatch)

    def fail_on_second(_target, index):
        if index == 3:
            raise RuntimeError("injected")

    with pytest.raises(RuntimeError, match="injected"):
        wipe_managed_instance(root, fail_on_second, clear_locator=False)
    assert read_verified_registry(root) == ["backups\\owned.db"]

    wipe_managed_instance(root, clear_locator=False)
    assert not root.exists()


def test_parent_swap_at_delete_boundary_is_rejected(tmp_path, monkeypatch):
    root, owned = make_instance(tmp_path, monkeypatch)
    original_parent = root / "backups-original"
    outside = tmp_path / "outside"
    outside.mkdir()
    decoy = outside / "owned.db"
    decoy.write_bytes(b"outside")

    def swap_parent(target, _index):
        if target == owned:
            target.parent.rename(original_parent)
            subprocess.run(
                ["cmd.exe", "/c", "mklink", "/J", str(target.parent), str(outside)],
                check=True,
                capture_output=True,
            )

    with pytest.raises(RuntimeError, match="parent changed"):
        wipe_managed_instance(root, swap_parent, clear_locator=False)

    assert decoy.read_bytes() == b"outside"
    assert (original_parent / "owned.db").read_bytes() == b"owned"
    assert (root / "state" / "managed-files-v1.txt").exists()


def test_owned_webview_state_tree_is_removed(tmp_path, monkeypatch):
    root, _ = make_instance(tmp_path, monkeypatch)
    cache = root / "state" / "webview2" / "EBWebView" / "Cache"
    cache.mkdir(parents=True)
    (cache / "index.bin").write_bytes(b"cache")
    wipe_managed_instance(root, clear_locator=False)
    assert not root.exists()


@pytest.mark.skipif(not hasattr(__import__("os").path, "isjunction"), reason="Windows junction contract")
def test_webview_parent_swap_at_delete_boundary_is_rejected(tmp_path, monkeypatch):
    import subprocess
    root, _ = make_instance(tmp_path, monkeypatch)
    cache = root / "state" / "webview2" / "Cache"
    cache.mkdir(parents=True)
    owned = cache / "index.bin"
    owned.write_bytes(b"owned")
    original = root / "state" / "webview2" / "Cache-original"
    outside = tmp_path / "outside-webview"
    outside.mkdir()
    decoy = outside / "index.bin"
    decoy.write_bytes(b"outside")

    def swap(target, _index):
        if target == owned:
            cache.rename(original)
            subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(cache), str(outside)], check=True, capture_output=True)

    with pytest.raises(RuntimeError, match="reparse point|escaped containment"):
        wipe_managed_instance(root, clear_locator=False, before_webview_delete=swap)
    assert decoy.read_bytes() == b"outside"
    assert (original / "index.bin").read_bytes() == b"owned"


@pytest.mark.skipif(not hasattr(__import__("os").path, "isjunction"), reason="Windows junction contract")
def test_webview_junction_rejected_before_database_delete(tmp_path, monkeypatch):
    import subprocess

    root, _ = make_instance(tmp_path, monkeypatch)
    outside = tmp_path / "outside-cache"
    outside.mkdir()
    decoy = outside / "decoy.bin"
    decoy.write_bytes(b"outside")
    link = root / "state" / "webview2"
    subprocess.run(["cmd.exe", "/c", "mklink", "/J", str(link), str(outside)], check=True, capture_output=True)
    with pytest.raises(RuntimeError, match="WebView state root is unsafe"):
        wipe_managed_instance(root, clear_locator=False)
    assert (root / "data" / "wealthos.db").read_bytes() == b"database"
    assert decoy.read_bytes() == b"outside"


@pytest.mark.parametrize("unsafe", [r"backups\CON", r"backups\..\outside.db", r"backups\\server\share.db"])
def test_authenticated_registry_still_rejects_device_traversal_and_unc(tmp_path, monkeypatch, unsafe):
    root, owned = make_instance(tmp_path, monkeypatch)
    monkeypatch.setattr("scripts.managed_wipe.read_verified_registry", lambda _root: [unsafe])

    with pytest.raises(RuntimeError, match="unsafe path"):
        wipe_managed_instance(root, clear_locator=False)

    assert owned.exists()
    assert (root / "data" / "wealthos.db").exists()
