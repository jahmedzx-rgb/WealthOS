import re
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend/src"
ROUTER = (FRONTEND / "AppRouter.tsx").read_text(encoding="utf-8")
REGISTRY = (FRONTEND / "operations/operationRegistry.ts").read_text(encoding="utf-8")
LANGUAGE = (FRONTEND / "context/LanguageContext.tsx").read_text(encoding="utf-8")

ALLOWED = {"WealthOS", "PDF", "XLSX", "CSV", "IBAN", "VAT", "SAR", "USD", "EUR", "GBP"}


def _has_untranslated_english(value: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z0-9&.-]*", value)
    return any(word not in ALLOWED for word in words)


def _route_sources() -> list[tuple[str, Path]]:
    imports = {
        name: FRONTEND / f"{module}.tsx"
        for name, module in re.findall(r"const\s+(\w+)=lazy\(\(\)=>import\('([^']+)'\)", ROUTER)
    }
    routes = re.findall(r'<Route\s+path="([^"]+)"\s+element=\{<(\w+)', ROUTER, re.S)
    return [(route, imports[component]) for route, component in routes if component in imports]


def _visible_raw_copy(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    found: list[str] = []
    for match in re.finditer(r">([^<>{}\r\n]*[A-Za-z][^<>{}\r\n]*)</[A-Za-z]", text):
        value = match.group(1).strip()
        if value and _has_untranslated_english(value):
            found.append(f"line {text.count(chr(10), 0, match.start(1)) + 1}: {value}")
    for match in re.finditer(r'\b(?:placeholder|aria-label|data-tooltip|eyebrow|subtitle)="([^"]*[A-Za-z][^"]*)"', text):
        value = match.group(1).strip()
        if _has_untranslated_english(value):
            found.append(f"line {text.count(chr(10), 0, match.start(1)) + 1} [{value}]")
    return sorted(set(found))


@pytest.mark.parametrize("route,source", _route_sources(), ids=lambda value: str(value))
def test_route_has_no_direct_untranslated_system_copy(route: str, source: Path):
    gaps = _visible_raw_copy(source)
    assert gaps == [], f"{route} -> {source.relative_to(ROOT).as_posix()}\n" + "\n".join(gaps)


def test_every_operation_registry_title_and_description_has_arabic_copy():
    gaps: list[str] = []
    for operation_id, body in re.findall(r"['\"]?([\w-]+)['\"]?\s*:\s*\{(.*?)\n\s*\},", REGISTRY, re.S):
        for field in ("title", "description"):
            match = re.search(rf"\b{field}:\s*'([^']+)'", body)
            if match and f"'{match.group(1)}':" not in LANGUAGE:
                gaps.append(f"/operations/{operation_id} [{field}] {match.group(1)}")
    assert gaps == [], "\n".join(gaps)


def test_property_route_family_is_explicitly_present_in_matrix():
    routes = {route for route, _ in _route_sources()}
    assert {"/properties", "/properties/income", "/properties/expenses"} <= routes
