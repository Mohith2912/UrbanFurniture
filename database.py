"""Small DB-API adapter: SQLite for offline development, PostgreSQL for hosting."""
import os
import re
import sqlite3
from decimal import Decimal
from urllib.parse import urlparse


def is_postgres(target):
    return str(target).startswith(('postgres://','postgresql://'))


def database_label(target):
    if not is_postgres(target):return 'SQLite local'
    return 'PostgreSQL local' if urlparse(target).hostname in ('127.0.0.1','localhost','::1') else 'PostgreSQL hosted'


class Row(dict):
    def __getitem__(self,key):
        return list(self.values())[key] if isinstance(key,int) else super().__getitem__(key)


class Cursor:
    def __init__(self,cursor):self.cursor=cursor
    def _row(self,row):
        if row is None:return None
        values=[int(v) if isinstance(v,Decimal) and v==v.to_integral_value() else float(v) if isinstance(v,Decimal) else v for v in row]
        return Row(zip([c.name for c in self.cursor.description],values))
    def fetchone(self):return self._row(self.cursor.fetchone())
    def fetchall(self):return [self._row(r) for r in self.cursor.fetchall()]
    def __iter__(self):return iter(self.fetchall())


class Postgres:
    dialect='postgres'
    def __init__(self,target):
        import psycopg
        self.conn=psycopg.connect(target,autocommit=True,connect_timeout=15)
        self.context=None
    def execute(self,sql,params=()):
        if sql=='BEGIN IMMEDIATE':
            return Cursor(self.conn.execute('SELECT pg_advisory_xact_lock(731251)'))
        sql=sql.replace('?','%s')
        if 'INSERT OR IGNORE INTO' in sql:
            sql=sql.replace('INSERT OR IGNORE INTO','INSERT INTO')+' ON CONFLICT DO NOTHING'
        return Cursor(self.conn.execute(sql,params))
    def executemany(self,sql,params):
        for row in params:self.execute(sql,row)
    def executescript(self,script):
        for statement in script.split(';'):
            if statement.strip():self.execute(statement)
    def commit(self):self.conn.commit()
    def close(self):self.conn.close()
    def __enter__(self):
        self.context=self.conn.transaction();self.context.__enter__()
        self.conn.execute('SELECT pg_advisory_xact_lock(731251)')
        return self
    def __exit__(self,*args):return self.context.__exit__(*args)


def connect(target):
    if is_postgres(target):return Postgres(target)
    conn=sqlite3.connect(target,timeout=15)
    conn.row_factory=sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    return conn


def postgres_schema(sql):
    sql=sql.replace('INTEGER PRIMARY KEY','BIGSERIAL PRIMARY KEY')
    sql=re.sub(r'\bINTEGER\b','BIGINT',sql)
    sql=re.sub(r'\bREAL\b','DOUBLE PRECISION',sql)
    sql=sql.replace(' COLLATE NOCASE','')
    sql=sql.replace('DEFAULT CURRENT_TIMESTAMP','DEFAULT (CURRENT_TIMESTAMP::text)')
    statements=[s.strip() for s in sql.split(';') if s.strip()]
    # Contacts must exist before the optional contact FK on users.
    contacts=[s for s in statements if s.startswith('CREATE TABLE IF NOT EXISTS contacts(')]
    return ';\n'.join(contacts+[s for s in statements if s not in contacts])+';'


def load_env(path):
    """Read a local .env without printing secrets or overriding process variables."""
    if not path.exists():return
    for raw in path.read_text(encoding='utf-8-sig').splitlines():
        raw=raw.strip()
        if not raw or raw.startswith('#') or '=' not in raw:continue
        key,value=raw.split('=',1)
        if key in {'DATABASE_URL','URBAN_SECRET','URBAN_DB','URBAN_HOST','URBAN_HTTPS','PORT'}:
            os.environ.setdefault(key,value.strip().strip('\"\''))
