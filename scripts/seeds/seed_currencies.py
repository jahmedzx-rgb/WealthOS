from app.core.models.currency import Currency


def seed_currencies(db):
    currencies = [
        Currency(
            code="USD",
            name="US Dollar",
            symbol="$",
        ),
        Currency(
            code="SAR",
            name="Saudi Riyal",
            symbol="﷼",
        ),
        Currency(
            code="EUR",
            name="Euro",
            symbol="€",
        ),
        Currency(
            code="GBP",
            name="British Pound",
            symbol="£",
        ),
    ]

    db.add_all(currencies)
from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_currencies(db)
        db.commit()
        print("Currencies seeded successfully.")
    finally:
        db.close()
