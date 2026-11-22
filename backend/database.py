"""Database configuration using SQLAlchemy for Neon PostgreSQL.

The `DATABASE_URL` environment variable (set in `.env`) contains the full
PostgreSQL connection string, e.g.:

```
postgres://user:password@myproject.neon.tech/mydb?sslmode=require
```

SQLAlchemy's `create_engine` automatically picks up the `sslmode=require`
parameter, so no extra SSL handling is needed.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Read connection URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL environment variable not set."
                      " Please configure it in .env or the deployment environment.")

# Create SQLAlchemy engine
engine = create_engine(
    DATABASE_URL,
    echo=False,          # Set True for verbose SQL logging during development
    future=True,
)

# Session factory used in FastAPI dependencies
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

# Base class for model definitions
Base = declarative_base()

def get_db():
    """FastAPI dependency that provides a database session and ensures it is closed.
    Usage::

        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
