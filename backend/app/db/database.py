from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv(dotenv_path=".env")

DATABASE_URL = os.getenv("DATABASE_URL")

if DATABASE_URL and DATABASE_URL.startswith("sqlite"):
    print("Using SQLite database")
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
elif DATABASE_URL:
    print("Using PostgreSQL (shared team database)")
    # Supabase/Production often requires SSL
    engine = create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
        connect_args={"sslmode": "require"} if "supabase" in DATABASE_URL or "sslmode" not in DATABASE_URL else {}
    )
else:
    print("DATABASE_URL not set. Falling back to SQLite.")
    engine = create_engine(
        "sqlite:///./local.db",
        connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False
)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
