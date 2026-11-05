import ctypes
import hashlib
import secrets
import socket
import threading
import webbrowser
import subprocess
import os
from urllib.parse import urlsplit

import uvicorn

from scripts.service_readiness import wait_for_http_health


ERROR_ALREADY_EXISTS = 183
COMPACT_WINDOW_SIZE = (600, 500)
MAIN_WINDOW_SIZE = (1280, 820)
CONTINUE_SETUP_BUTTON = 1001
EXIT_WITHOUT_SAVING_BUTTON = 1002


class _TaskDialogButton(ctypes.Structure):
    _fields_ = [("button_id", ctypes.c_int), ("text", ctypes.c_wchar_p)]


class _TaskDialogConfig(ctypes.Structure):
    _fields_ = [("size", ctypes.c_uint), ("parent", ctypes.c_void_p), ("instance", ctypes.c_void_p),
                ("flags", ctypes.c_uint), ("common_buttons", ctypes.c_uint), ("title", ctypes.c_wchar_p),
                ("main_icon", ctypes.c_void_p), ("instruction", ctypes.c_wchar_p), ("content", ctypes.c_wchar_p),
                ("button_count", ctypes.c_uint), ("buttons", ctypes.POINTER(_TaskDialogButton)),
                ("default_button", ctypes.c_int), ("radio_count", ctypes.c_uint), ("radio_buttons", ctypes.c_void_p),
                ("default_radio", ctypes.c_int), ("verification", ctypes.c_wchar_p), ("expanded", ctypes.c_wchar_p),
                ("expanded_control", ctypes.c_wchar_p), ("collapsed_control", ctypes.c_wchar_p),
                ("footer_icon", ctypes.c_void_p), ("footer", ctypes.c_wchar_p), ("callback", ctypes.c_void_p),
                ("callback_data", ctypes.c_ssize_t), ("width", ctypes.c_uint)]


def confirm_incomplete_setup_exit(task_dialog=None) -> bool:
    """True only when the user explicitly chooses the destructive exit action."""
    buttons = (_TaskDialogButton * 2)(
        _TaskDialogButton(CONTINUE_SETUP_BUTTON, "متابعة الإعداد / Continue setup"),
        _TaskDialogButton(EXIT_WITHOUT_SAVING_BUTTON, "الخروج دون حفظ / Exit without saving"),
    )
    config = _TaskDialogConfig()
    config.size = ctypes.sizeof(config)
    config.title = "WealthOS"
    config.instruction = "لم يكتمل الإعداد / Setup is not complete"
    config.content = "لن تُحفظ البيانات المدخلة جزئياً.\nPartially entered information will not be saved."
    config.button_count = 2
    config.buttons = buttons
    config.default_button = CONTINUE_SETUP_BUTTON
    selected = ctypes.c_int(CONTINUE_SETUP_BUTTON)
    runner = task_dialog or ctypes.WinDLL("comctl32", use_last_error=True).TaskDialogIndirect
    try:
        result = runner(ctypes.byref(config), ctypes.byref(selected), None, None)
    except Exception:
        # Closing an incomplete setup must fail closed if the native confirmation
        # dialog cannot be created or returns through an unexpected host failure.
        return False
    return result == 0 and selected.value == EXIT_WITHOUT_SAVING_BUTTON


class _LastInputInfo(ctypes.Structure):
    _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]


class WindowsInputActivityProbe:
    """Reports new genuine Windows input only while this process owns the foreground window."""
    def __init__(self):
        self._last_tick = None

    def __call__(self) -> bool:
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        info = _LastInputInfo(ctypes.sizeof(_LastInputInfo), 0)
        if not user32.GetLastInputInfo(ctypes.byref(info)):
            return False
        process_id = ctypes.c_ulong()
        foreground = user32.GetForegroundWindow()
        user32.GetWindowThreadProcessId(foreground, ctypes.byref(process_id))
        changed = self._last_tick is not None and info.dwTime != self._last_tick
        self._last_tick = info.dwTime
        return bool(changed and process_id.value == os.getpid())


def current_principal_sid() -> str:
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command",
         "[System.Security.Principal.WindowsIdentity]::GetCurrent().User.Value"],
        capture_output=True, text=True, timeout=10, check=False,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    sid = result.stdout.strip()
    if result.returncode != 0 or not sid.startswith("S-1-"):
        raise RuntimeError("Unable to bind the local unlock session to this Windows account.")
    return sid


def stop_server(server, server_thread, listener) -> None:
    server.should_exit = True
    server_thread.join(timeout=15)
    if server_thread.is_alive():
        server.force_exit = True
        server_thread.join(timeout=5)
    listener.close()
    if server_thread.is_alive():
        raise RuntimeError("The local WealthOS service did not shut down cleanly.")
def acquire_single_instance_mutex(installation_id: str):
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    identity_hash = hashlib.sha256(installation_id.encode("ascii")).hexdigest()[:24]
    handle = kernel32.CreateMutexW(None, False, f"Local\\WealthOS-Beta-{identity_hash}")
    if not handle:
        raise OSError(ctypes.get_last_error(), "Unable to create the WealthOS instance mutex.")
    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        kernel32.CloseHandle(handle)
        return None
    return handle


def is_internal_navigation(url: str, origin: str) -> bool:
    target = urlsplit(url)
    expected = urlsplit(origin)
    return target.scheme == expected.scheme and target.netloc == expected.netloc


def safe_external_https(url: str) -> bool:
    if any(ord(character) < 32 for character in url):
        return False
    parsed = urlsplit(url)
    return parsed.scheme == "https" and bool(parsed.hostname) and parsed.username is None and parsed.password is None


def window_dimensions(mode: str, work_area: tuple[int, int]) -> tuple[int, int]:
    if mode not in {"compact", "main"}:
        raise ValueError("Unknown desktop window mode.")
    target = COMPACT_WINDOW_SIZE if mode == "compact" else MAIN_WINDOW_SIZE
    margin = 32 if mode == "compact" else 48
    minimum = (520, 440) if mode == "compact" else (720, 560)
    return min(target[0], max(minimum[0], work_area[0] - margin)), min(target[1], max(minimum[1], work_area[1] - margin))


def apply_window_mode(window, mode: str, work_area: tuple[int, int]) -> None:
    width, height = window_dimensions(mode, work_area)
    window.restore()
    window.resize(width, height)
    window.move(max(0, (work_area[0] - width) // 2), max(0, (work_area[1] - height) // 2))
    if mode == "main":
        window.maximize()


def harden_core_webview(native, origin: str, external_opener=webbrowser.open):
    settings = native.Settings
    settings.AreDevToolsEnabled = False
    settings.AreDefaultContextMenusEnabled = False
    settings.AreBrowserAcceleratorKeysEnabled = False
    settings.IsWebMessageEnabled = False
    settings.IsStatusBarEnabled = False

    def navigation_starting(_sender, args):
        if not is_internal_navigation(str(args.Uri), origin):
            args.Cancel = True

    def new_window(_sender, args):
        target = str(args.Uri)
        args.Handled = True
        if bool(getattr(args, "IsUserInitiated", False)) and safe_external_https(target):
            external_opener(target)

    def permission_requested(_sender, args):
        from Microsoft.Web.WebView2.Core import CoreWebView2PermissionState
        args.State = CoreWebView2PermissionState.Deny

    def download_starting(_sender, args):
        args.Cancel = True

    native.NavigationStarting += navigation_starting
    native.NewWindowRequested += new_window
    native.PermissionRequested += permission_requested
    native.DownloadStarting += download_starting
    return (navigation_starting, new_window, permission_requested, download_starting)


def run_desktop_app(app, installation_id: str, webview_storage_root, icon_path) -> int:
    mutex = acquire_single_instance_mutex(installation_id)
    if mutex is None:
        return 0

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    origin = f"http://127.0.0.1:{port}"
    capability = secrets.token_urlsafe(48)
    bootstrap_path = f"/desktop-bootstrap/{capability}"
    app.state.desktop_origin = origin
    app.state.launch_capability = capability
    app.state.bootstrap_path = bootstrap_path
    app.state.installation_id = installation_id
    app.state.local_principal_sid = current_principal_sid()
    app.state.unlock_sessions = {}
    app.state.user_activity_probe = WindowsInputActivityProbe()
    config = uvicorn.Config(app, log_level="warning", access_log=False)
    server = uvicorn.Server(config)
    server_thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=False)
    server_thread.start()

    try:
        if not wait_for_http_health(f"{origin}/health", timeout_seconds=120.0):
            server.should_exit = True
            server_thread.join(timeout=10)
            raise RuntimeError("The local WealthOS service did not become ready.")

        import webview
        webview.settings["ALLOW_DOWNLOADS"] = False
        webview.settings["ALLOW_FILE_URLS"] = False
        webview.settings["OPEN_EXTERNAL_LINKS_IN_BROWSER"] = False
        webview.settings["REMOTE_DEBUGGING_PORT"] = None

        work_area = (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))
        compact_width, compact_height = window_dimensions("compact", work_area)
        window = webview.create_window(
            "WealthOS Beta",
            f"{origin}{bootstrap_path}",
            width=compact_width,
            height=compact_height,
            min_size=(520, 440),
            background_color="#f4f6f8",
        )
        mode_lock = threading.Lock()

        def set_window_mode(mode: str) -> None:
            if mode not in {"compact", "main"}:
                return
            with mode_lock:
                apply_window_mode(window, mode, work_area)

        app.state.desktop_window_mode_callback = set_window_mode

        def closing():
            if bool(getattr(app.state, "setup_incomplete", True)) and not confirm_incomplete_setup_exit():
                return False
            server.should_exit = True

        window.events.closing += closing

        def harden_native_webview():
            native = window.native.browser.webview.CoreWebView2
            window._wealthos_security_handlers = harden_core_webview(native, origin)

        webview.start(
            harden_native_webview,
            gui="edgechromium",
            debug=False,
            private_mode=True,
            storage_path=str(webview_storage_root),
            icon=str(icon_path),
        )
        return 0
    finally:
        app.state.desktop_window_mode_callback = None
        try:
            stop_server(server, server_thread, listener)
        finally:
            ctypes.WinDLL("kernel32", use_last_error=True).CloseHandle(mutex)
