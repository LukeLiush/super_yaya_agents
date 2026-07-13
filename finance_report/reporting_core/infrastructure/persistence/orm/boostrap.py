from __future__ import annotations

import logging

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker

from finance_report.reporting_core.infrastructure.persistence.orm.mapping import (
    metadata, start_mappers,
)

logger = logging.getLogger(__name__)


def init_persistence(db_url: str = "sqlite:///:memory:", create_tables: bool = True) -> sessionmaker:
    """Wire mappers, engine and schema once. Returns a session factory for the UoW."""
    start_mappers()
    engine: Engine = create_engine(db_url, echo=True)
    if create_tables:
        metadata.create_all(engine, checkfirst=True)  # use Alembic for real databases migration
        logger.info("Schema created for %s", db_url)
    return sessionmaker(bind=engine, expire_on_commit=False)
