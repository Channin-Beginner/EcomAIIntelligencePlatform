from collections.abc import Generator
from contextlib import contextmanager
import logging

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, RowMapping
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

logger = logging.getLogger("ecom.database")

_engine: Engine | None = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    global _engine, _SessionLocal
    if _engine is None:
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        _SessionLocal = sessionmaker(bind=_engine, autoflush=False, autocommit=False)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal


def get_db() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def db_session() -> Generator[Session, None, None]:
    db = get_session_factory()()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Database transaction rolled back")
        raise
    finally:
        db.close()


def row_to_dict(row: RowMapping | None) -> dict | None:
    if row is None:
        return None
    return dict(row)


def rows_to_dicts(rows: list[RowMapping]) -> list[dict]:
    return [dict(r) for r in rows]


def fetch_one(db: Session, sql: str, params: dict | None = None) -> dict | None:
    result = db.execute(text(sql), params or {})
    row = result.mappings().first()
    return row_to_dict(row)


def fetch_all(db: Session, sql: str, params: dict | None = None) -> list[dict]:
    result = db.execute(text(sql), params or {})
    return rows_to_dicts(result.mappings().all())


def execute(db: Session, sql: str, params: dict | None = None) -> int:
    result = db.execute(text(sql), params or {})
    return result.rowcount
