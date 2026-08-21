import logging
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SQLite_DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "trustguard.db"))

# Fetch Database URL from Environment Variable (e.g. set in production)
# Fallback to local SQLite if not configured
DATABASE_URL = os.environ.get("DATABASE_URL")
IS_PRODUCTION = os.environ.get("TRUSTGUARD_ENV", "development").lower() == "production"

engine = None
is_sqlite = False

from sqlalchemy.exc import DatabaseError, OperationalError

if DATABASE_URL and DATABASE_URL.startswith(("postgresql://", "postgres://")):
    try:
        # Check if we need to replace postgres:// with postgresql:// for SQLAlchemy compatibility
        if DATABASE_URL.startswith("postgres://"):
            DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        
        # 🔴 Item 3: Production-Grade SQLAlchemy PostgreSQL Connection Pool
        pool_size = int(os.environ.get("DB_POOL_SIZE", "10"))
        max_overflow = int(os.environ.get("DB_MAX_OVERFLOW", "20"))
        pool_timeout = int(os.environ.get("DB_POOL_TIMEOUT", "30"))
        pool_recycle = int(os.environ.get("DB_POOL_RECYCLE", "1800"))

        engine = create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_timeout=pool_timeout,
            pool_recycle=pool_recycle,
            connect_args={"connect_timeout": 10}
        )
        # Test connection
        conn = engine.connect()
        conn.close()
        logger.info("[SUCCESS] Database Connection: Connected to production PostgreSQL database with connection pooling.")
    except (OperationalError, DatabaseError) as e:
        if IS_PRODUCTION:
            # 🔴 Item 1: Refuse startup in production mode — zero silent SQLite fallback!
            raise RuntimeError(
                f"🔴 PRODUCTION DATABASE FAILURE: Failed to connect to PostgreSQL database ({e}). "
                f"Silent fallback to SQLite is strictly forbidden in production."
            ) from e
        logger.warning(f"[WARNING] PostgreSQL Connection failed ({e}). Falling back to local SQLite database in development mode.")
        engine = None


if engine is None:
    if IS_PRODUCTION:
        raise RuntimeError("🔴 PRODUCTION DATABASE FAILURE: DATABASE_URL must be configured and connected in production mode.")

    DATABASE_URL = f"sqlite:///{SQLite_DB_PATH}"
    is_sqlite = True
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    logger.info(f"[INFO] Database Connection: Using local SQLite database at {SQLite_DB_PATH}")

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()

# Note: Database schema management is managed via Alembic migrations (alembic upgrade head).


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()