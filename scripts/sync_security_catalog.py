"""Refresh the offline Saudi listed-securities directory from Sahmk."""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.settings import settings
from app.investing.services.market_security_search import SahmkMarketSecuritySearch


def main() -> None:
    provider = SahmkMarketSecuritySearch(settings.SAHMK_API_KEY)
    offset = 0
    records: list[dict] = []
    while True:
        payload = provider._load(f"{provider.BASE_URL}/companies/?limit=100&offset={offset}")
        batch = payload.get("results", [])
        records.extend(item for item in batch if item.get("symbol") and str(item.get("status", "active")).lower() == "active")
        offset += len(batch)
        if not batch or offset >= int(payload.get("total", offset)):
            break
    target = Path(__file__).resolve().parents[1] / "app" / "investing" / "data" / "saudi_securities.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} active Saudi securities.")


if __name__ == "__main__":
    main()
