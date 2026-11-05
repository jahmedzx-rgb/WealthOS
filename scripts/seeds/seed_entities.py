from app.core.models.entity import Entity


def seed_entities(db):
    entities = [
        Entity(
            code="PERSONAL",
            name="Personal",
            entity_type="INDIVIDUAL",
            base_currency_id=1,
        ),
        Entity(
            code="FAMILY",
            name="Family",
            entity_type="FAMILY",
            base_currency_id=2,
        ),
    ]

    db.add_all(entities)
from app.database.engine import SessionLocal

if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_entities(db)
        db.commit()
        print("Entities seeded successfully.")
    finally:
        db.close()
