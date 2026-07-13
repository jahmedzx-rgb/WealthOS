from app.database.engine import SessionLocal
from app.models.account import Account


def main():
    db = SessionLocal()

    try:
        accounts = [
            Account(
                code=1000,
                name="Assets",
                account_type="ASSET",
                normal_balance="DEBIT",
                is_header=True,
                allow_posting=False,
            ),
            Account(
                code=2000,
                name="Liabilities",
                account_type="LIABILITY",
                normal_balance="CREDIT",
                is_header=True,
                allow_posting=False,
            ),
            Account(
                code=3000,
                name="Equity",
                account_type="EQUITY",
                normal_balance="CREDIT",
                is_header=True,
                allow_posting=False,
            ),
            Account(
                code=4000,
                name="Revenue",
                account_type="REVENUE",
                normal_balance="CREDIT",
                is_header=True,
                allow_posting=False,
            ),
            Account(
                code=5000,
                name="Expenses",
                account_type="EXPENSE",
                normal_balance="DEBIT",
                is_header=True,
                allow_posting=False,
            ),
        ]

        db.add_all(accounts)
        db.commit()

        print("Chart of Accounts seeded successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    main()