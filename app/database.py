import os
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime, Float, Integer
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL")

engine = None
SessionLocal = None
Base = declarative_base()


class RequestLog(Base):
    __tablename__ = "requestLogs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requestId = Column(String(50), unique=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Request info
    method = Column(String(10))
    path = Column(String(500))
    queryParams = Column(Text, nullable=True)
    clientIp = Column(String(50))
    userAgent = Column(String(500), nullable=True)

    # Request body (for non-file requests)
    requestContentType = Column(String(100), nullable=True)
    requestFilename = Column(String(255), nullable=True)
    requestFileSizeKb = Column(Float, nullable=True)

    # Response info
    statusCode = Column(Integer)
    responseBody = Column(Text, nullable=True)

    # Timing
    processingTimeMs = Column(Float)


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
