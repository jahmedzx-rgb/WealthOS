import sys
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from sqlalchemy import text
import hmac

import app.database.model_registry

from app.api.v1.router import api_router
from app.core.settings import settings
from app.security.local_lock import validate_session
from app.security.web_auth import SESSION_COOKIE, csrf_is_valid, get_session
from app.accounting.services.period_lock import PeriodClosedError
from app.core.models.user import User
from app.database.engine import SessionLocal


def _configure_utf8_console() -> None:
    """Keep Arabic request data safe in Windows development logs."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="backslashreplace")


_configure_utf8_console()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="WealthOS Personal Finance & Investment Platform",
)

trusted_hosts = [host.strip() for host in settings.TRUSTED_HOSTS.split(",") if host.strip()]
app.add_middleware(TrustedHostMiddleware, allowed_hosts=trusted_hosts)

FRONTEND_DIST = Path(__file__).resolve().parent / "frontend" / "dist"


@app.exception_handler(PeriodClosedError)
async def closed_period_error(_request: Request, exc: PeriodClosedError):
    return JSONResponse(status_code=409, content={"detail": str(exc), "code": "ACCOUNTING_PERIOD_CLOSED"})


@app.middleware("http")
async def security_controls(request: Request, call_next):
    request_app = request.scope.get("app")
    app_state = getattr(request_app, "state", None)
    desktop_origin = getattr(app_state, "desktop_origin", None)
    capability = getattr(app_state, "launch_capability", None)
    if desktop_origin and capability:
        expected_host = desktop_origin.removeprefix("http://")
        if request.client is None or request.client.host != "127.0.0.1":
            return JSONResponse(status_code=403, content={"detail": "Loopback access only."})
        if request.headers.get("host") != expected_host or any(
            header in request.headers for header in ("forwarded", "x-forwarded-for", "x-forwarded-host", "x-forwarded-proto")
        ):
            return JSONResponse(status_code=400, content={"detail": "Invalid local host."})
        if request.url.path == "/health":
            return await call_next(request)
        if request.url.path == getattr(app_state, "bootstrap_path", ""):
            response = RedirectResponse("/", status_code=303)
            response.set_cookie("wealthos_launch", capability, httponly=True, samesite="strict", path="/")
            return response
        supplied = request.cookies.get("wealthos_launch", "")
        if not hmac.compare_digest(supplied, capability):
            return JSONResponse(status_code=401, content={"detail": "Missing local launch capability."})
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            if request.headers.get("origin") != desktop_origin or request.headers.get("sec-fetch-site") not in {"same-origin", "none"}:
                return JSONResponse(status_code=403, content={"detail": "Invalid local request origin."})
    public_account_paths = {
        "/api/v1/account/setup-status",
        "/api/v1/account/setup",
        "/api/v1/account/unlock-status",
        "/api/v1/account/unlock",
        "/api/v1/account/recover",
    }
    public_web_paths = {"/api/v1/auth/register", "/api/v1/auth/login"}
    if request.url.path.startswith("/api/v1/"):
        if settings.WEB_MODE:
            with SessionLocal() as db:
                session = get_session(db, request.cookies.get(SESSION_COOKIE, ""))
                if request.url.path not in public_web_paths and session is None:
                    return JSONResponse(status_code=401, content={"detail": {"key": "auth.required"}})
                if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path not in public_web_paths:
                    if session is None or not csrf_is_valid(request, session):
                        return JSONResponse(status_code=403, content={"detail": {"key": "auth.csrf_invalid"}})
        else:
            with SessionLocal() as db:
                user = db.query(User).filter(User.id == settings.LOCAL_USER_ID, User.is_active.is_(True)).first()
                if request.url.path not in public_account_paths and (user is None or not user.setup_completed):
                    return JSONResponse(status_code=423, content={"detail": "Local setup is required."})
                if user is not None and user.setup_completed and user.password_hash:
                    store = getattr(app_state, "unlock_sessions", {})
                    app_state.unlock_sessions = store
                    activity_probe = getattr(app_state, "user_activity_probe", None)
                    genuine_activity = bool(activity_probe and activity_probe())
                    unlocked = validate_session(
                        store, request.cookies.get("wealthos_unlock", ""), user_id=user.id,
                        installation_id=str(getattr(app_state, "installation_id", "test-installation")),
                        principal_sid=str(getattr(app_state, "local_principal_sid", "test-principal")),
                        security_version=user.security_state_version, inactivity_minutes=user.lock_timeout_minutes,
                        user_activity=genuine_activity,
                    )
                    request.state.account_unlocked = unlocked
                    if request.url.path not in public_account_paths and not unlocked:
                        return JSONResponse(status_code=423, content={"detail": "Local unlock is required."})
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > 10 * 1024 * 1024:
                return JSONResponse(status_code=413, content={"detail": "Request is too large."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header."})
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'none'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self'; "
        "img-src 'self' data: blob:; "
        "font-src 'self' data:; "
        "worker-src 'self' blob:; "
        "manifest-src 'self'; "
        "base-uri 'none'; "
        "form-action 'self'; "
        "object-src 'none'; "
        "frame-ancestors 'none'"
    )
    return response

app.include_router(api_router)


@app.get("/health", tags=["System"])
def health():
    return {"status": "healthy", "application": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/ready", tags=["System"])
def ready():
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}


@app.get("/")
def root():
    if settings.WEB_MODE and (FRONTEND_DIST / "index.html").is_file():
        return FileResponse(FRONTEND_DIST / "index.html")
    return {
        "application": settings.APP_NAME,
        "status": "running",
        "version": settings.APP_VERSION,
    }


@app.get("/{requested_path:path}", include_in_schema=False)
def web_frontend(requested_path: str):
    if not settings.WEB_MODE:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if requested_path == "api" or requested_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    requested_file = (FRONTEND_DIST / requested_path).resolve()
    try:
        requested_file.relative_to(FRONTEND_DIST.resolve())
    except ValueError:
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    if requested_file.is_file():
        return FileResponse(requested_file)
    index_file = FRONTEND_DIST / "index.html"
    if index_file.is_file():
        return FileResponse(index_file)
    return JSONResponse(status_code=503, content={"detail": "Web frontend is unavailable."})
