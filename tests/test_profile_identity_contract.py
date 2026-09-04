from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROFILE = (ROOT / "frontend/src/pages/userProfile.ts").read_text(encoding="utf-8")
HYDRATOR = (ROOT / "frontend/src/components/BetaProfileInitializer.tsx").read_text(encoding="utf-8")


def test_stale_unscoped_browser_profile_is_not_a_source_of_truth():
    assert "parsed.source!=='backend'" in PROFILE
    assert "Number.isInteger(parsed.accountId)" in PROFILE
    assert "source:'backend'" in PROFILE
    assert "fullName:tester" not in HYDRATOR


def test_backend_profile_overwrites_authenticated_browser_cache_on_startup():
    assert "getAccountProfile()" in HYDRATOR
    assert "fullName:profile.full_name" in HYDRATOR
    assert "profile.id" in HYDRATOR
    assert "saveUserProfile" in HYDRATOR
    assert "setLanguage(profile.preferred_language)" in HYDRATOR


def test_profile_language_is_not_reloaded_on_every_navigation():
    hydration_effect = HYDRATOR.split("getAccountProfile()", 1)[1]
    assert "[setLanguage]" in hydration_effect
    assert "location.pathname,location.search,location.hash,setLanguage" not in HYDRATOR
