import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
LANGUAGE_CONTEXT_PATH = FRONTEND / "context" / "LanguageContext.tsx"
LANGUAGE_CONTEXT = LANGUAGE_CONTEXT_PATH.read_text(encoding="utf-8")

# User-visible product/brand strings that are intentionally identical in both languages.
ALLOWED_VISIBLE_LATIN = {
    "WealthOS", "PDF", "XLSX", "CSV", "IBAN", "VAT", "SAR", "USD", "EUR", "GBP",
}

USER_DATA_FIELDS = (
    "name", "account_name", "bank_name", "card_name", "broker_name", "provider_name",
    "product_name", "description", "reason", "reference", "symbol", "portfolio_number", "iban",
)


def _tsx_sources():
    for folder in ("pages", "operations", "components"):
        yield from (FRONTEND / folder).rglob("*.tsx")


def _has_unallowed_latin(value: str) -> bool:
    words = re.findall(r"[A-Za-z][A-Za-z0-9&.-]*", value)
    return any(word not in ALLOWED_VISIBLE_LATIN for word in words)


def _location(path: Path, text: str, offset: int, value: str) -> str:
    return f"{path.relative_to(ROOT).as_posix()}:{text.count(chr(10), 0, offset) + 1}: {value.strip()}"


def test_every_literal_translation_call_has_an_arabic_value():
    missing: list[str] = []
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for key in re.findall(r"\bt\(\s*['\"]([^'\"]+)['\"]\s*\)", text):
            if f"'{key}':" not in LANGUAGE_CONTEXT:
                missing.append(f"{path.relative_to(ROOT).as_posix()}: {key}")
    assert sorted(set(missing)) == []


def test_no_raw_english_text_nodes_remain_in_user_visible_frontend():
    violations: list[str] = []
    raw_text = re.compile(r">([^<>{}\r\n]*[A-Za-z][^<>{}\r\n]*)</[A-Za-z]")
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for match in raw_text.finditer(text):
            value = match.group(1).strip()
            if value and _has_unallowed_latin(value):
                violations.append(_location(path, text, match.start(1), value))
    assert sorted(violations) == []


def test_no_raw_english_user_visible_attributes_remain():
    violations: list[str] = []
    visible_attribute = re.compile(r'\b(?:placeholder|aria-label|data-tooltip|eyebrow|subtitle)="([^"]*[A-Za-z][^"]*)"')
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for match in visible_attribute.finditer(text):
            value = match.group(1)
            if _has_unallowed_latin(value):
                violations.append(_location(path, text, match.start(1), value))
    assert sorted(violations) == []


def test_translation_is_not_applied_to_user_entered_fields():
    violations: list[str] = []
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for field in USER_DATA_FIELDS:
            pattern = re.compile(rf"\bt\(\s*[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*\.{re.escape(field)}\s*\)")
            for match in pattern.finditer(text):
                violations.append(_location(path, text, match.start(), match.group(0)))
    assert sorted(violations) == []


def test_language_switch_changes_presentation_not_route_or_form_state():
    assert "document.documentElement.lang=language" in LANGUAGE_CONTEXT
    assert "document.documentElement.dir=language==='ar'?'rtl':'ltr'" in LANGUAGE_CONTEXT
    assert "localStorage.setItem('wealthos-language',next)" in LANGUAGE_CONTEXT
    assert "window.location" not in LANGUAGE_CONTEXT
    assert "navigate(" not in LANGUAGE_CONTEXT


def test_literal_frontend_status_and_error_messages_use_translation():
    violations: list[str] = []
    pattern = re.compile(r"\bset(?:Message|Status|Error)\(\s*['\"]([^'\"]*[A-Za-z][^'\"]*)['\"]\s*\)")
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            violations.append(_location(path, text, match.start(), match.group(1)))
    assert sorted(violations) == []


def test_literal_input_defaults_do_not_bypass_localization():
    violations: list[str] = []
    pattern = re.compile(r'<input\b[^>]*\b(?:value|defaultValue)="([^"]*[A-Za-z][^"]*)"[^>]*>')
    for path in _tsx_sources():
        text = path.read_text(encoding="utf-8")
        for match in pattern.finditer(text):
            value = match.group(1)
            if _has_unallowed_latin(value):
                violations.append(_location(path, text, match.start(1), value))
    assert sorted(violations) == []


def test_backend_api_errors_have_arabic_mappings_when_shown_by_frontend():
    details: set[str] = set()
    for path in (ROOT / "app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        details.update(re.findall(r"\bdetail\s*=\s*['\"]([^'\"]*[A-Za-z][^'\"]*)['\"]", text))
    missing = sorted(detail for detail in details if f"'{detail}':" not in LANGUAGE_CONTEXT)
    assert missing == []
