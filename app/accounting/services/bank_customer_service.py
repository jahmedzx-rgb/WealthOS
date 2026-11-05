from app.accounting.models.bank_account import BankCustomer

def bank_key(name):
    return ' '.join(name.strip().casefold().split())

def customer_number(db,user_id,bank_name):
    row=db.query(BankCustomer).filter_by(user_id=user_id,bank_key=bank_key(bank_name)).first()
    return row.customer_number if row else None

def save_customer_number(db,user_id,bank_name,value,replace=False):
    key=bank_key(bank_name)
    row=db.query(BankCustomer).filter_by(user_id=user_id,bank_key=key).with_for_update().first()
    number=(value or '').strip()
    if row:
        if not replace and (not number or number==row.customer_number):return
        if not replace:raise ValueError('This bank already has a different Customer Number. Edit an existing account to correct it.')
        if number:row.customer_number=number
        else:db.delete(row)
    elif number:
        db.add(BankCustomer(user_id=user_id,bank_key=key,customer_number=number))
