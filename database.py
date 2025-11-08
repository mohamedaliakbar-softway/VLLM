import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,  # Test connections before using
    pool_recycle=60,  # Recycle connections every 60 seconds (Replit timeout fix)
    pool_size=5,  # Smaller pool for Replit
    max_overflow=2,  # Limit overflow connections
    connect_args={
        "connect_timeout": 10,
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    } if DATABASE_URL and 'postgresql' in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
