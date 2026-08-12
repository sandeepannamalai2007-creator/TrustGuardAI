from database import engine, Base

# Import db_models so all table classes are registered on Base
# before create_all() runs. (Importing api_models here was a bug —
# those are just Pydantic request/response schemas, not ORM tables,
# and "backend.api_models" also doesn't exist as a package when this
# script is run directly from inside backend/.)
import db_models  # noqa: F401

Base.metadata.create_all(bind=engine)

try:
    print("✅ Database created successfully!")
except UnicodeEncodeError:
    print("[SUCCESS] Database created successfully!")
