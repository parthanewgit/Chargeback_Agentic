from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

Base = declarative_base()
connect_args = {'check_same_thread': False} if settings.DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def create_schema(bind=engine) -> None:
	from app.persistence import models

	Base.metadata.create_all(bind=bind)
	if bind.dialect.name == 'sqlite':
		with bind.begin() as connection:
			columns = {row[1] for row in connection.exec_driver_sql('PRAGMA table_info(cases)').fetchall()}
			if 'case_data' not in columns:
				connection.exec_driver_sql('ALTER TABLE cases ADD COLUMN case_data TEXT')
			if 'payload' not in columns:
				connection.exec_driver_sql('ALTER TABLE cases ADD COLUMN payload TEXT')
