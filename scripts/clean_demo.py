"""One-time, explicitly authorized cleanup of the original demo workspace.

Refuses to clear a database containing unrecognized business masters.
Preserves staff accounts and core accounting configuration, with a safety backup.
"""
import sqlite3
from contextlib import closing
from datetime import datetime
from pathlib import Path

root=Path(__file__).resolve().parents[1]
database=root/'data'/'urban.sqlite3'
expected={
    'contacts':{'Nimesh Pathak','Azure Furniture','Studio North'},
    'products':{'Oak office chair','Walnut writing desk','Linen three-seat sofa','Round dining table'},
    'analytics':{'Retail showroom','Showroom purchases'},
    'budgets':{'Showroom revenue','Inventory purchases'},
}
with closing(sqlite3.connect(database)) as conn:
    conn.execute('PRAGMA foreign_keys=ON')
    for table,names in expected.items():
        actual={row[0] for row in conn.execute(f'SELECT name FROM {table}')}
        if not actual<=names:raise SystemExit(f'Refusing to clear {table}: non-demo records exist.')
    if conn.execute('SELECT COUNT(*) FROM expenses').fetchone()[0]:
        raise SystemExit('Non-demo expenses exist. Review before resetting.')
    backups=root/'data'/'backups';backups.mkdir(exist_ok=True)
    path=backups/f'before-clean-start-{datetime.now():%Y%m%d-%H%M%S}.sqlite3'
    with closing(sqlite3.connect(path)) as backup:conn.backup(backup)
    with conn:
        conn.execute('BEGIN IMMEDIATE')
        for table in ['payment_requests','expenses','stock_moves','payments','entry_lines','entries','documents','order_lines','orders','budgets','analytics']:
            conn.execute(f'DELETE FROM {table}')
        conn.execute("DELETE FROM users WHERE role='contact'")
        conn.execute('DELETE FROM contacts');conn.execute('DELETE FROM products')
        conn.execute("DELETE FROM audit WHERE entity!='users'")
        uid=conn.execute("SELECT id FROM users WHERE role='admin' ORDER BY id LIMIT 1").fetchone()[0]
        conn.execute('INSERT INTO audit(user_id,action,entity,detail) VALUES(?,?,?,?)',(uid,'Clean workspace started','system','Demo records removed at owner request. Staff accounts and accounting configuration preserved.'))
    assert conn.execute('PRAGMA foreign_key_check').fetchall()==[]
    print('Demo business records removed. Staff accounts preserved:',conn.execute('SELECT COUNT(*) FROM users').fetchone()[0])
    print('Recovery backup:',path)
