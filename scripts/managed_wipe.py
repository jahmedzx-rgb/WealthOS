from pathlib import Path
from typing import Callable
import winreg
import re
import os

from scripts.managed_files import ALLOWED_PREFIXES, REGISTRY_KEY, REGISTRY_RELATIVE_PATH, read_verified_registry


EXACT_DATABASE_FILES = ("wealthos.db", "wealthos.db-wal", "wealthos.db-shm")
WINDOWS_RESERVED_NAMES = re.compile(
    r"^(con|prn|aux|nul|com[1-9]|lpt[1-9])(?:\..*)?$", re.IGNORECASE
)
WEBVIEW_STATE_DIRECTORY = Path("state") / "webview2"


def _validated_owned_tree(root: Path) -> tuple[list[Path], list[Path]]:
    tree = root / WEBVIEW_STATE_DIRECTORY
    if not tree.exists():
        return [], []
    if not tree.is_dir() or tree.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(tree)):
        raise RuntimeError("The managed WebView state root is unsafe.")
    files, directories = [], []
    for current, directory_names, file_names in os.walk(tree, topdown=True, followlinks=False):
        current_path = Path(current)
        if current_path.resolve(strict=True) != current_path or root not in current_path.parents:
            raise RuntimeError("The managed WebView state escaped containment.")
        for name in directory_names:
            child = current_path / name
            if child.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(child)):
                raise RuntimeError("The managed WebView state contains a reparse point.")
            directories.append(child)
        for name in file_names:
            child = current_path / name
            if not child.is_file() or child.is_symlink():
                raise RuntimeError("The managed WebView state contains an unsafe file.")
            files.append(child)
    return files, sorted(directories, key=lambda path: len(path.parts), reverse=True)


def _revalidate_webview_target(root: Path, target: Path, *, directory: bool) -> None:
    tree = root / WEBVIEW_STATE_DIRECTORY
    if tree.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(tree)):
        raise RuntimeError("The managed WebView state root changed after verification.")
    resolved_tree = tree.resolve(strict=True)
    if target.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(target)):
        raise RuntimeError("The managed WebView state contains a changed reparse point.")
    resolved = target.resolve(strict=True)
    if resolved != target or resolved_tree not in resolved.parents:
        raise RuntimeError("The managed WebView state escaped containment after verification.")
    if directory and not target.is_dir():
        raise RuntimeError("A managed WebView directory changed after verification.")
    if not directory and not target.is_file():
        raise RuntimeError("A managed WebView file changed after verification.")


def _validated_registered_target(root: Path, relative: str) -> Path:
    normalized = relative.replace("\\", "/")
    filename = normalized.split("/", 1)[1] if "/" in normalized else ""
    if (
        not normalized.startswith(ALLOWED_PREFIXES)
        or "/" in filename
        or ".." in normalized
        or ":" in normalized
        or normalized.startswith(("\\", "//"))
        or WINDOWS_RESERVED_NAMES.fullmatch(filename)
    ):
        raise RuntimeError("The managed-file registry contains an unsafe path.")
    target = root / Path(normalized)
    if target.parent.resolve(strict=True).parent != root:
        raise RuntimeError("A registered managed file escaped containment.")
    return target


def wipe_managed_instance(
    root: Path,
    before_delete: Callable[[Path, int], None] | None = None,
    *,
    clear_locator: bool = True,
    before_webview_delete: Callable[[Path, int], None] | None = None,
) -> None:
    root = root.resolve(strict=True)
    entries = read_verified_registry(root)
    targets = [root / "data" / name for name in EXACT_DATABASE_FILES]
    targets.extend(_validated_registered_target(root, entry) for entry in entries)
    webview_files, webview_directories = _validated_owned_tree(root)
    for target in targets:
        if target.exists() and (not target.is_file() or target.is_symlink()):
            raise RuntimeError("A managed wipe target is unsafe.")
    for index, target in enumerate(targets):
        if target.exists():
            if target.parent.resolve(strict=True).parent != root:
                raise RuntimeError("A managed wipe parent changed after verification.")
            if before_delete:
                before_delete(target, index)
            # Re-resolve immediately before the path-based unlink.  The callback is
            # used by the deterministic race test to model a parent swap at the
            # last possible boundary.
            if target.parent.resolve(strict=True).parent != root:
                raise RuntimeError("A managed wipe parent changed after verification.")
            if not target.is_file() or target.is_symlink():
                raise RuntimeError("A managed wipe target changed after verification.")
            target.unlink()

    for index, target in enumerate(webview_files):
        if before_webview_delete:
            before_webview_delete(target, index)
        _revalidate_webview_target(root, target, directory=False)
        target.unlink()
    for directory in webview_directories:
        _revalidate_webview_target(root, directory, directory=True)
        directory.rmdir()
    webview_root = root / WEBVIEW_STATE_DIRECTORY
    if webview_root.exists():
        if webview_root.resolve(strict=True) != webview_root or webview_root.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(webview_root)):
            raise RuntimeError("The managed WebView state root changed after verification.")
        webview_root.rmdir()

    registry = root / REGISTRY_RELATIVE_PATH
    unknown = []
    for child in ("data", "backups", "diagnostics"):
        unknown.extend((root / child).iterdir())
    unknown.extend(path for path in (root / "state").iterdir() if path != registry)
    if unknown:
        raise RuntimeError("Unknown files were preserved; the managed wipe is incomplete.")

    if registry.exists():
        registry.unlink()
    for child in ("data", "backups", "diagnostics", "state"):
        (root / child).rmdir()
    root.rmdir()
    if clear_locator:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REGISTRY_KEY, 0, winreg.KEY_SET_VALUE) as key:
            for value in ("InstallationId", "ManagedFilesHmacKey", "MetadataVersion"):
                try:
                    winreg.DeleteValue(key, value)
                except FileNotFoundError:
                    pass
