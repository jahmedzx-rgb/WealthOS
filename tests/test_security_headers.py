from pathlib import Path
import asyncio
import re

from starlette.requests import Request
from starlette.responses import Response

from main import security_controls


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_DIRECTIVES = {
    "default-src": "'none'",
    "script-src": "'self'",
    "style-src": "'self' 'unsafe-inline'",
    "connect-src": "'self'",
    "img-src": "'self' data: blob:",
    "font-src": "'self' data:",
    "worker-src": "'self' blob:",
    "manifest-src": "'self'",
    "base-uri": "'none'",
    "form-action": "'self'",
    "object-src": "'none'",
    "frame-ancestors": "'none'",
}


def parse_policy(policy: str) -> dict[str, str]:
    return {
        parts[0]: " ".join(parts[1:])
        for directive in policy.split(";")
        if (parts := directive.strip().split())
    }


def test_security_headers_allow_only_required_same_origin_application_resources():
    request = Request({"type": "http", "method": "GET", "path": "/", "headers": []})

    async def call_next(_request):
        return Response()

    response = asyncio.run(security_controls(request, call_next))
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["x-content-type-options"] == "nosniff"
    assert parse_policy(response.headers["content-security-policy"]) == EXPECTED_DIRECTIVES


def test_frontend_bootstrap_assets_are_same_origin_and_allowed_by_csp():
    html = (ROOT / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
    script_sources = re.findall(r'<script[^>]+src="([^"]+)"', html)
    stylesheet_tags = re.findall(r'<link[^>]+rel="stylesheet"[^>]*>', html)
    stylesheet_sources = [
        match.group(1)
        for tag in stylesheet_tags
        if (match := re.search(r'href="([^"]+)"', tag))
    ]
    assert script_sources
    assert stylesheet_sources
    assert all(source.startswith("/assets/") for source in script_sources + stylesheet_sources)
    assert EXPECTED_DIRECTIVES["script-src"] == "'self'"
    assert "'self'" in EXPECTED_DIRECTIVES["style-src"]
