from __future__ import annotations

import re
import sqlite3
from pathlib import Path
from typing import Any


class SqlQueryAdvisorService:
    FORBIDDEN_KEYWORDS = {'insert', 'update', 'delete', 'drop', 'alter', 'create', 'replace', 'attach', 'detach', 'vacuum', 'pragma writable_schema'}

    def __init__(self, default_db_path: str) -> None:
        self.default_db_path = str(Path(default_db_path))

    def schema_overview(self, db_path: str | None = None) -> dict[str, list[str]]:
        target = db_path or self.default_db_path
        with sqlite3.connect(target) as conn:
            tables = [row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            schema: dict[str, list[str]] = {}
            for table in tables:
                columns = [row[1] for row in conn.execute(f"PRAGMA table_info({table})")]
                schema[table] = columns
        return schema

    def extract_sql(self, text: str) -> str | None:
        fenced = re.search(r'```sql\s*(.*?)```', text, re.IGNORECASE | re.DOTALL)
        if fenced:
            return fenced.group(1).strip()
        inline = re.search(r'\b(select|with)\b.*', text, re.IGNORECASE | re.DOTALL)
        if inline:
            return inline.group(0).strip()
        return None

    def is_read_only(self, query: str) -> bool:
        normalized = re.sub(r'--.*?(\r?\n|$)', ' ', query.lower())
        normalized = re.sub(r'/\*.*?\*/', ' ', normalized, flags=re.DOTALL).strip().rstrip(';')
        if not normalized:
            return False
        if any(keyword in normalized for keyword in self.FORBIDDEN_KEYWORDS):
            return False
        return normalized.startswith('select') or normalized.startswith('with') or normalized.startswith('pragma table_info')

    def execute_read_only(self, query: str, *, db_path: str | None = None, row_limit: int = 50) -> dict[str, Any]:
        if not self.is_read_only(query):
            raise ValueError('Solo se permiten consultas SQL de lectura.')
        target = db_path or self.default_db_path
        wrapped = f'SELECT * FROM ({query.rstrip().rstrip(";")}) LIMIT {int(row_limit)}'
        with sqlite3.connect(target) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(wrapped).fetchall()
        result_rows = [{key: row[key] for key in row.keys()} for row in rows]
        return {
            'query': query.strip(),
            'row_count': len(result_rows),
            'rows': result_rows,
            'db_path': target,
            'sources': [f'sqlite:{Path(target).name}'],
        }

    def advise(self, text: str, *, db_path: str | None = None) -> dict[str, Any]:
        query = self.extract_sql(text)
        if query:
            execution = self.execute_read_only(query, db_path=db_path)
            execution['summary'] = f"Consulta ejecutada en solo lectura con {execution['row_count']} filas."
            execution['schema'] = self.schema_overview(db_path=db_path)
            return execution
        schema = self.schema_overview(db_path=db_path)
        return {
            'query': None,
            'row_count': 0,
            'rows': [],
            'schema': schema,
            'summary': 'No encontre una consulta SQL explicita. Te muestro el esquema disponible para planear una consulta segura.',
            'sources': [f'tabla:{table}' for table in schema.keys()],
        }
