"""Database engine and session setup.

Uses SQLite by default (zero setup). Set the DATABASE_URL environment variable
to point at PostgreSQL or any other SQLAlchemy-supported database in production.
"""
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./shortener.db")

# Some hosts hand out "postgres://" URLs, which SQLAlchemy does not accept.
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    """FastAPI dependency that gives each request its own DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
