from app.investing.models.broker import Broker


def seed_brokers(db):
    brokers = [
        Broker(
            code="ABYAN",
            name="Abyan Capital",
            country="Saudi Arabia",
            website="https://abyan.sa",
        ),
        Broker(
            code="GTN",
            name="GTN",
            country="UAE",
            website="https://www.gtn.com",
        ),
        Broker(
            code="IBKR",
            name="Interactive Brokers",
            country="United States",
            website="https://www.interactivebrokers.com",
        ),
        Broker(
            code="SCHWAB",
            name="Charles Schwab",
            country="United States",
            website="https://www.schwab.com",
        ),
    ]

    db.add_all(brokers)

from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_brokers(db)
        db.commit()
        print("Brokers seeded successfully.")
    finally:
        db.close()
