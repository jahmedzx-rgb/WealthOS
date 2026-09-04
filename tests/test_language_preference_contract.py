from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ACCOUNT_API = (ROOT / "app/api/v1/account.py").read_text(encoding="utf-8")
LANGUAGE_CONTEXT = (ROOT / "frontend/src/context/LanguageContext.tsx").read_text(encoding="utf-8")
ACCOUNT_SERVICE = (ROOT / "frontend/src/services/accountService.ts").read_text(encoding="utf-8")


def test_language_switch_is_persisted_to_the_authenticated_local_account():
    assert '@router.patch("/preferences/language")' in ACCOUNT_API
    assert "user.preferred_language = request.preferred_language" in ACCOUNT_API
    assert "updatePreferredLanguage" in ACCOUNT_SERVICE
    assert "updatePreferredLanguage(next)" in LANGUAGE_CONTEXT


def test_failed_language_persistence_rolls_back_the_optimistic_switch():
    assert ".catch(()=>setLanguage(previous))" in LANGUAGE_CONTEXT
