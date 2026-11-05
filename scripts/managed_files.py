import hashlib
import hmac
import os
from pathlib import Path
import winreg


REGISTRY_RELATIVE_PATH = Path("state") / "managed-files-v1.txt"
ALLOWED_PREFIXES = ("backups/", "diagnostics/")
REGISTRY_KEY = r"Software\WealthOS\Beta"
HMAC_VALUE = "ManagedFilesHmacKey"
FORMAT = "wealthos-managed-files-v1"


def load_hmac_key() -> bytes:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY) as key:
        value, value_type = winreg.QueryValueEx(key, HMAC_VALUE)
    if value_type != winreg.REG_BINARY or not isinstance(value, bytes) or len(value) != 32:
        raise RuntimeError("The managed-file integrity key is invalid.")
    return value


def _signature(lines: list[str], key: bytes) -> str:
    body = FORMAT + "\n" + "\n".join(sorted(lines)) + "\n"
    return hmac.new(key, body.encode("utf-8"), hashlib.sha256).hexdigest()


def read_verified_registry(instance_root: Path) -> list[str]:
    registry = instance_root / REGISTRY_RELATIVE_PATH
    if not registry.exists():
        return []
    if not registry.is_file() or registry.is_symlink():
        raise RuntimeError("The managed-file registry path is unsafe.")
    raw = registry.read_text(encoding="utf-8").splitlines()
    if len(raw) < 2 or raw[0] != FORMAT or not raw[-1].startswith("hmac-sha256="):
        raise RuntimeError("The managed-file registry format is invalid.")
    lines = raw[1:-1]
    expected = _signature(lines, load_hmac_key())
    supplied = raw[-1].split("=", 1)[1]
    if not hmac.compare_digest(expected, supplied):
        raise RuntimeError("The managed-file registry integrity check failed.")
    return lines


def register_managed_file(instance_root: Path, file_path: Path) -> None:
    root = instance_root.resolve(strict=True)
    resolved = file_path.resolve(strict=True)
    try:
        relative = resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise RuntimeError("A managed file escaped the registered instance.") from error
    if not relative.startswith(ALLOWED_PREFIXES) or "/" in relative.split("/", 1)[1]:
        raise RuntimeError("A managed file is outside the versioned ownership registry.")
    lines = sorted(set(read_verified_registry(root)) | {relative.replace("/", "\\")})
    registry = root / REGISTRY_RELATIVE_PATH
    body = FORMAT + "\n" + "\n".join(lines) + "\n"
    body += f"hmac-sha256={_signature(lines, load_hmac_key())}\n"
    temporary = registry.with_suffix(f".{os.getpid()}.tmp")
    temporary.write_text(body, encoding="utf-8")
    os.replace(temporary, registry)
