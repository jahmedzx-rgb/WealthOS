from app.database.engine import SessionLocal
from app.services.ledger_service import LedgerService


def main():
    db = SessionLocal()

    try:
        ledger = LedgerService(db)

        entry = ledger.post(
            description="First WealthOS Journal Entry"
        )

        print(f"Journal Entry ID: {entry.id}")
        print(f"Description: {entry.description}")

    finally:
        db.close()


if __name__ == "__main__":
    main()