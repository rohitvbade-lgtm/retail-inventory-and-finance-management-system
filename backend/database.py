import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./inventory_finance.db")

from sqlalchemy import text

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# Safe auto-migration for SQLite database
try:
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE discount_rules ADD COLUMN code VARCHAR(100);"))
            conn.commit()
        except Exception:
            pass
except Exception:
    pass

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

