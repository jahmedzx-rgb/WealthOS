import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database.base import Base
from app.accounting.models.bank_account import BankCustomer
from app.accounting.services.bank_customer_service import customer_number,save_customer_number

def test_shared_number_keeps_zeroes_isolates_users_and_requires_explicit_correction():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine,tables=[BankCustomer.__table__])
    db=sessionmaker(bind=engine)()
    save_customer_number(db,1,' SNB ','001234');db.commit()
    assert customer_number(db,1,'snb')=='001234'
    assert customer_number(db,2,'SNB') is None
    save_customer_number(db,1,'SNB','');db.commit()
    assert customer_number(db,1,'SNB')=='001234'
    with pytest.raises(ValueError):save_customer_number(db,1,'SNB','98765')
    save_customer_number(db,1,'SNB','00987',replace=True);db.commit()
    assert customer_number(db,1,'SNB')=='00987'
    save_customer_number(db,1,'SNB','',replace=True);db.commit()
    assert customer_number(db,1,'SNB') is None
    db.close();engine.dispose()
