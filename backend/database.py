from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLite_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "trustguard.db"))

# Fetch Database URL from Environment Variable (e.g. set in production)
# Fallback to local SQLite if not configured
DATABASE_URL = os.environ.get("DATABASE_URL")

engine = None
is_sqlite = False

if DATABASE_URL and (DATABASE_URL.startswith("postgresql://") or DATABASE_URL.startswith("postgres://")):
    try:
        # Check if we need to replace postgres:// with postgresql:// for SQLAlchemy compatibility
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
        engine = create_engine(DATABASE_URL)
        # Test connection
        conn = engine.connect()
        conn.close()
        print("[SUCCESS] Database Connection: Connected to PostgreSQL database.")
    except Exception as e:
        print(f"[WARNING] PostgreSQL Connection failed ({e}). Falling back to local SQLite database.")
        engine = None

if engine is None:
    DATABASE_URL = f"sqlite:///{SQLite_DB_PATH}"
    is_sqlite = True
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    print(f"[INFO] Database Connection: Using local SQLite database at {SQLite_DB_PATH}")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()