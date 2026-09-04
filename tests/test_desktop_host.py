from types import SimpleNamespace

from scripts.desktop_host import CONTINUE_SETUP_BUTTON, EXIT_WITHOUT_SAVING_BUTTON, apply_window_mode, confirm_incomplete_setup_exit, harden_core_webview, is_internal_navigation, safe_external_https, stop_server, window_dimensions
from app.security.local_lock import issue_session, session_token_hash, validate_session


def test_internal_navigation_stays_in_native_window():
    origin = "http://127.0.0.1:49152"
    assert is_internal_navigation(f"{origin}/settings/profile", origin)
    assert is_internal_navigation(f"{origin}/api/v1/account/me", origin)


def test_external_navigation_is_not_loaded_in_native_window():
    origin = "http://127.0.0.1:49152"
    assert not is_internal_navigation("https://example.com", origin)
    assert not is_internal_navigation("http://127.0.0.1:8765/", origin)


def test_only_canonical_https_without_credentials_is_external():
    assert safe_external_https("https://example.com/path")
    assert not safe_external_https("http://example.com")
    assert not safe_external_https("https://user:secret@example.com")
    assert not safe_external_https("javascript:alert(1)")
    assert not safe_external_https("https://example.com/\nunsafe")


def test_launcher_is_windowed_single_instance_desktop_host():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    launcher = (root / "beta_launcher.py").read_text(encoding="utf-8")
    build = (root / "scripts/build_beta.ps1").read_text(encoding="utf-8")
    host = (root / "scripts/desktop_host.py").read_text(encoding="utf-8")
    assert "run_desktop_app(app, installation_id, webview_storage_root, icon_path)" in launcher
    assert "webbrowser.open" not in launcher
    assert "--windowed" in build
    assert "CreateMutexW" in host
    assert 'gui="edgechromium"' in host
    assert "PermissionRequested" in host
    assert "IsWebMessageEnabled = False" in host
    assert 'icon=str(icon_path)' in host
    assert "wealthos-app-icon.ico" in launcher
    assert 'desktop_window_mode_callback' in host


def test_compact_and_main_window_modes_are_centered_and_bounded():
    assert window_dimensions("compact", (1920, 1080)) == (600, 500)
    assert window_dimensions("main", (1920, 1080)) == (1280, 820)
    assert window_dimensions("compact", (600, 500)) == (568, 468)
    window = SimpleNamespace(calls=[], restore=lambda: window.calls.append(("restore",)), resize=lambda w, h: window.calls.append(("resize", w, h)), move=lambda x, y: window.calls.append(("move", x, y)), maximize=lambda: window.calls.append(("maximize",)))
    apply_window_mode(window, "compact", (1920, 1080))
    assert window.calls == [("restore",), ("resize", 600, 500), ("move", 660, 290)]
    window.calls.clear()
    apply_window_mode(window, "main", (1920, 1080))
    assert window.calls[-1] == ("maximize",)


def test_invalid_window_mode_fails_closed():
    import pytest
    with pytest.raises(ValueError):
        window_dimensions("client-supplied", (1920, 1080))


def test_incomplete_setup_close_defaults_to_continuing_setup():
    def runner(_config, selected, _radio, _verification):
        import ctypes
        ctypes.cast(selected, ctypes.POINTER(ctypes.c_int)).contents.value = CONTINUE_SETUP_BUTTON
        return 0
    assert confirm_incomplete_setup_exit(runner) is False


def test_incomplete_setup_closes_only_after_explicit_exit_without_saving():
    def runner(_config, selected, _radio, _verification):
        import ctypes
        ctypes.cast(selected, ctypes.POINTER(ctypes.c_int)).contents.value = EXIT_WITHOUT_SAVING_BUTTON
        return 0
    assert confirm_incomplete_setup_exit(runner) is True


def test_incomplete_setup_close_fails_closed_when_native_dialog_fails():
    def runner(_config, _selected, _radio, _verification):
        raise OSError("native dialog unavailable")

    assert confirm_incomplete_setup_exit(runner) is False


class Event:
    def __init__(self):
        self.handlers = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


def test_runtime_policy_binds_and_blocks_navigation_popup_and_download():
    native = SimpleNamespace(
        Settings=SimpleNamespace(),
        NavigationStarting=Event(),
        NewWindowRequested=Event(),
        PermissionRequested=Event(),
        DownloadStarting=Event(),
    )
    opened = []
    handlers = harden_core_webview(native, "http://127.0.0.1:49152", opened.append)
    assert len(handlers) == 4
    assert native.Settings.AreDevToolsEnabled is False
    assert native.Settings.IsWebMessageEnabled is False
    navigation = SimpleNamespace(Uri="https://evil.invalid", Cancel=False)
    native.NavigationStarting.handlers[0](None, navigation)
    assert navigation.Cancel is True
    safe_popup = SimpleNamespace(Uri="https://example.com", IsUserInitiated=True, Handled=False)
    unsafe_popup = SimpleNamespace(Uri="javascript:alert(1)", IsUserInitiated=True, Handled=False)
    native.NewWindowRequested.handlers[0](None, safe_popup)
    native.NewWindowRequested.handlers[0](None, unsafe_popup)
    assert safe_popup.Handled and unsafe_popup.Handled
    assert opened == ["https://example.com"]
    download = SimpleNamespace(Cancel=False)
    native.DownloadStarting.handlers[0](None, download)
    assert download.Cancel is True


def test_shutdown_escalates_and_verifies_thread_exit():
    class Thread:
        def __init__(self): self.joins = 0
        def join(self, timeout): self.joins += 1
        def is_alive(self): return self.joins < 2
    server = SimpleNamespace(should_exit=False, force_exit=False)
    listener = SimpleNamespace(closed=False, close=lambda: setattr(listener, "closed", True))
    thread = Thread()
    stop_server(server, thread, listener)
    assert server.should_exit and server.force_exit and listener.closed
    assert thread.joins == 2


def test_background_requests_do_not_extend_inactivity():
    store = {}
    token = issue_session(store, user_id=1, installation_id="install", principal_sid="sid", security_version=1)
    session = store[session_token_hash(token)]
    original = session.last_activity_at
    assert validate_session(store, token, user_id=1, installation_id="install", principal_sid="sid", security_version=1, inactivity_minutes=15, user_activity=False)
    assert session.last_activity_at == original
    assert validate_session(store, token, user_id=1, installation_id="install", principal_sid="sid", security_version=1, inactivity_minutes=15, user_activity=True)
    assert session.last_activity_at >= original


def test_process_restart_invalidates_memory_only_unlock_session():
    first_store = {}
    token = issue_session(first_store, user_id=1, installation_id="install", principal_sid="sid", security_version=1)
    assert not validate_session({}, token, user_id=1, installation_id="install", principal_sid="sid", security_version=1, inactivity_minutes=15)
