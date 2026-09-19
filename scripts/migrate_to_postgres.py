"""Copy the current SQLite workspace to an EMPTY configured PostgreSQL database.

Preserves staff credentials, posted snapshots, primary keys and audit history.
Call with DATABASE_URL set, or use data/native-database-url for the native install.
Never overwrites a populated destination. Stop the application during migration.
"""
import os
import sqlite3
import sys
from pathlib import Path
from contextlib import closing
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from database import connect

root=Path(__file__).resolve().parents[1]
url=os.environ.get('DATABASE_URL') or (root/'data'/'native-database-url').read_text().strip()
create_app(url,testing=True)
tables=['contacts','users','products','accounts','journals','analytics','budgets','orders','order_lines','documents','entries','entry_lines','payments','stock_moves','expenses','payment_requests','audit']
with closing(sqlite3.connect(root/'data'/'urban.sqlite3')) as source, closing(connect(url)) as dest:
    source.row_factory=sqlite3.Row
    assert dest.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0,'Destination has users; refusing to overwrite.'
    with dest:
        for table in tables:
            source_rows=source.execute('SELECT * FROM '+table+' ORDER BY id').fetchall()
            if source_rows:
                columns=list(source_rows[0].keys())
                query=f'INSERT INTO {table} ('+','.join(columns)+') VALUES ('+','.join('?' for _ in columns)+')'
                dest.executemany(query,[tuple(r) for r in source_rows])
                dest.execute(f"SELECT setval(pg_get_serial_sequence('{table}','id'),(SELECT MAX(id) FROM {table}),true)")
            print(table,len(source_rows))
        for key,value in source.execute('SELECT key,value FROM workspace'):
            dest.execute('INSERT INTO workspace(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',(key,value))
        for table in tables:
            assert source.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]==dest.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0]
print('Migration complete. Counts verified; source SQLite database retained.')
