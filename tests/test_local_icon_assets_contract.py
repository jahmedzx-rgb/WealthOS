import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_rendered_images_do_not_reference_remote_hosts():
    source = "\n".join(path.read_text(encoding="utf-8") for path in (FRONTEND / "src").rglob("*.tsx"))
    assert not re.search(r"<img[^>]+(?:src|srcSet)\s*=\s*[{'\"]https?://", source, re.IGNORECASE)


def test_every_registered_platform_icon_is_packaged_locally():
    source = (FRONTEND / "src" / "utils" / "platformIcons.ts").read_text(encoding="utf-8")
    paths = re.findall(r"['\"](/platforms/[^'\"]+)['\"]", source)
    assert paths
    assert all((FRONTEND / "public" / path.removeprefix("/")).is_file() for path in paths)


def test_every_preloaded_broker_icon_is_packaged_locally():
    source = (FRONTEND / "src" / "AppRouter.tsx").read_text(encoding="utf-8")
    match = re.search(r"\[([^]]+)\]\.forEach\(name=>\{const image=new Image", source)
    assert match
    names = re.findall(r"['\"]([^'\"]+)['\"]", match.group(1))
    assert names
    assert all((FRONTEND / "public" / "brokers" / f"{name}.png").is_file() for name in names)
