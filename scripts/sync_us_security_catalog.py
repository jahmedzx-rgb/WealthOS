"""Refresh the offline US listed-securities symbol directory."""
import csv
import io
import json
from pathlib import Path
from urllib.request import Request, urlopen


FILES = (
    ("https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt", "NASDAQ"),
    ("https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt", "US"),
)


def main() -> None:
    records: dict[str, dict] = {}
    for url, default_exchange in FILES:
        request = Request(url, headers={"User-Agent": "WealthOS/0.1"})
        with urlopen(request, timeout=30) as response:
            text = response.read().decode("utf-8-sig")
        for row in csv.DictReader(io.StringIO(text), delimiter="|"):
            symbol = (row.get("Symbol") or row.get("ACT Symbol") or "").strip().upper()
            name = (row.get("Security Name") or "").strip()
            if not symbol or not name or symbol.startswith("File Creation Time") or row.get("Test Issue") == "Y":
                continue
            exchange_code = (row.get("Exchange") or "").strip()
            exchange = {"N": "NYSE", "A": "NYSE_AMERICAN", "P": "NYSE_ARCA", "Z": "BATS", "V": "IEX"}.get(exchange_code, default_exchange)
            upper_name = name.upper()
            security_type = "ETF" if row.get("ETF") == "Y" else "REIT" if " REIT" in upper_name or "REAL ESTATE INVESTMENT TRUST" in upper_name else "STOCK"
            records[symbol] = {"symbol": symbol, "name": name, "exchange": exchange, "security_type": security_type}
    target = Path(__file__).resolve().parents[1] / "app" / "investing" / "data" / "us_securities.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(sorted(records.values(), key=lambda item: item["symbol"]), ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(f"Saved {len(records)} active US securities.")


if __name__ == "__main__":
    main()
