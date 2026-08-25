from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

import pytest

from iabv_v15.services.roles.sql_query_advisor_service import SqlQueryAdvisorService


def _db_path() -> Path:
    base = Path(__file__).resolve().parents[1] / 'data' / 'test_runs'
    base.mkdir(parents=True, exist_ok=True)
    root = base / f'sql_{uuid4().hex}'
    root.mkdir(parents=True, exist_ok=True)
    db_path = root / 'sample.sqlite'
    with sqlite3.connect(db_path) as conn:
        conn.execute('CREATE TABLE customers (id INTEGER PRIMARY KEY, name TEXT, city TEXT)')
        conn.execute("INSERT INTO customers (name, city) VALUES ('Ana', 'Bogota')")
        conn.execute("INSERT INTO customers (name, city) VALUES ('Luis', 'Medellin')")
    return db_path


def test_sql_query_advisor_executes_read_only_query() -> None:
    db_path = _db_path()
    service = SqlQueryAdvisorService(str(db_path))

    result = service.execute_read_only('SELECT name, city FROM customers ORDER BY id')

    assert result['row_count'] == 2
    assert result['rows'][0]['name'] == 'Ana'
    assert result['sources'] == [f'sqlite:{db_path.name}']


def test_sql_query_advisor_rejects_write_queries() -> None:
    db_path = _db_path()
    service = SqlQueryAdvisorService(str(db_path))

    with pytest.raises(ValueError):
        service.execute_read_only("DELETE FROM customers WHERE id = 1")


def test_sql_query_advisor_reports_schema_when_query_is_missing() -> None:
    db_path = _db_path()
    service = SqlQueryAdvisorService(str(db_path))

    result = service.advise('Muestrame las tablas disponibles')

    assert result['query'] is None
    assert 'customers' in result['schema']
    assert 'tabla:customers' in result['sources']
