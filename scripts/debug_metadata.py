from app.database.base import Base

import app.models.account
import app.models.journal_entry
import app.models.journal_line

print(Base.metadata.tables.keys())