import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import managed_files
from scripts.managed_wipe import wipe_managed_instance


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="wealthos-parent-swap-") as temporary:
        base = Path(temporary)
        root = base / "instance"
        for child in ("data", "backups", "diagnostics", "state"):
            (root / child).mkdir(parents=True)
        database = root / "data" / "wealthos.db"
        database.write_bytes(b"database")
        owned = root / "backups" / "owned.db"
        owned.write_bytes(b"owned")
        outside = base / "outside"
        outside.mkdir()
        decoy = outside / "wealthos.db"
        decoy.write_bytes(b"outside-decoy")
        key = b"f" * 32
        original_loader = managed_files.load_hmac_key
        managed_files.load_hmac_key = lambda: key
        try:
            managed_files.register_managed_file(root, owned)
            registry = root / managed_files.REGISTRY_RELATIVE_PATH
            before = {
                "database": digest(database),
                "owned": digest(owned),
                "outside_decoy": digest(decoy),
                "registry": digest(registry),
            }
            original_parent = root / "data-original"

            def swap_parent(target: Path, _index: int) -> None:
                if target == database:
                    target.parent.rename(original_parent)
                    subprocess.run(
                        ["cmd.exe", "/c", "mklink", "/J", str(target.parent), str(outside)],
                        check=True,
                        capture_output=True,
                    )

            error = None
            try:
                wipe_managed_instance(root, swap_parent, clear_locator=False)
            except RuntimeError as exc:
                error = str(exc)

            result = {
                "scenario": "deterministic-parent-swap-at-pre-delete-hook",
                "execution": "exact source module represented by candidate source provenance",
                "nonzero_equivalent_exception": error is not None,
                "error": error,
                "outside_decoy_hash_unchanged": digest(decoy) == before["outside_decoy"],
                "database_hash_unchanged": digest(original_parent / "wealthos.db") == before["database"],
                "owned_hash_unchanged": digest(owned) == before["owned"],
                "authenticated_registry_hash_unchanged": digest(registry) == before["registry"],
            }
            print(json.dumps(result))
        finally:
            managed_files.load_hmac_key = original_loader


if __name__ == "__main__":
    main()
