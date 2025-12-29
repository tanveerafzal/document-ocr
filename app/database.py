import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = None
SessionLocal = None
Base = declarative_base()


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(String(50), unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Request info
    method = Column(String(10))
    path = Column(String(500))
    query_params = Column(Text, nullable=True)
    client_ip = Column(String(50))
    user_agent = Column(String(500), nullable=True)

    # Request body (for non-file requests)
    request_content_type = Column(String(100), nullable=True)
    request_filename = Column(String(255), nullable=True)
    request_file_size_kb = Column(Float, nullable=True)

    # Response info
    status_code = Column(Integer)
    response_body = Column(Text, nullable=True)

    # Timing
    processing_time_ms = Column(Float)


def init_db():
    """Initialize database connection and create tables."""
    global engine, SessionLocal

    if not DATABASE_URL:
        raise ValueError("DATABASE_URL environment variable is not set")

    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create tables
    Base.metadata.create_all(bind=engine)


def get_db():
    """Get database session."""
    if SessionLocal is None:
        init_db()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_session():
    """Get a database session directly (non-generator)."""
    if SessionLocal is None:
        init_db()
    return SessionLocal()
