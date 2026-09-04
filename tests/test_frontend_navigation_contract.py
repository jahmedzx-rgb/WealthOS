import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
ROUTER = (FRONTEND / "AppRouter.tsx").read_text(encoding="utf-8")
SIDEBAR = (FRONTEND / "components" / "layout" / "Sidebar.tsx").read_text(encoding="utf-8")


def _route_patterns() -> list[str]:
    return re.findall(r'<Route\s+path="([^"]+)"', ROUTER)


def _matches_route(path: str, pattern: str) -> bool:
    path = path.split("?", 1)[0]
    expression = "/".join("[^/]+" if part.startswith(":") else re.escape(part) for part in pattern.split("/"))
    return re.fullmatch(expression, path) is not None


def test_every_literal_internal_link_has_a_registered_route():
    patterns = _route_patterns()
    links: set[str] = set()
    for source in FRONTEND.rglob("*.tsx"):
        text = source.read_text(encoding="utf-8")
        links.update(re.findall(r'(?:to|navigate\()\s*=*\s*["\'](/[^"\'`$]*)["\']', text))
        links.update(re.findall(r'(?:route|path)\s*:\s*["\'](/[^"\'`$]*)["\']', text))

    missing = sorted(
        link for link in links
        if link != "/" and not any(_matches_route(link, pattern) for pattern in patterns)
    )
    assert missing == []


def test_sidebar_submenu_labels_use_the_translation_function():
    untranslated = [
        "Executive Summary",
        "Stocks",
        "Deposits",
        "Investment Cash Flows",
        "Alternative Investments",
        "Saving Circles",
        "Cash",
        "Brokers",
        "Financial Platforms",
        "Monthly Snapshots",
        "Property Income",
        "Property Expenses",
    ]
    for label in untranslated:
        assert f">{label}<" not in SIDEBAR
        assert f"{{t('{label}')}}" in SIDEBAR
