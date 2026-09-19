"""Initialize a private, loopback-only native PostgreSQL installation for this app.

Requires the official PostgreSQL binaries under LOCALAPPDATA/UrbanFurniture.
Generates credentials into ignored local files; never prints credentials.
"""
import json
import os
import secrets
import subprocess
from pathlib import Path
import psycopg
from psycopg import sql

root=Path(__file__).resolve().parents[1]
binary=Path(os.environ['LOCALAPPDATA'])/'UrbanFurniture'/'PostgreSQL17'/'pgsql'/'bin'
cluster=root/'data'/'postgres'
config_path=root/'data'/'postgres-private.json'
assert (binary/'initdb.exe').exists(), 'Install native PostgreSQL binaries first.'
if config_path.exists():
    config=json.loads(config_path.read_text())
else:
    config=dict(port=55432,admin_password=secrets.token_urlsafe(32),app_password=secrets.token_urlsafe(32),binary=str(binary),cluster=str(cluster))
    config_path.write_text(json.dumps(config),encoding='utf-8')
if not (cluster/'PG_VERSION').exists():
    password_file=root/'data'/'.pg-init-password'
    password_file.write_text(config['admin_password'],encoding='utf-8')
    try:
        subprocess.run([str(binary/'initdb.exe'),'-D',str(cluster),'-U','urban_admin','--pwfile='+str(password_file),'--encoding=UTF8','--locale=C','-A','scram-sha-256'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
    finally:password_file.unlink(missing_ok=True)
status=subprocess.run([str(binary/'pg_ctl.exe'),'-D',str(cluster),'status'],capture_output=True,creationflags=subprocess.CREATE_NO_WINDOW)
if status.returncode:
    subprocess.run([str(binary/'pg_ctl.exe'),'-D',str(cluster),'-l',str(root/'data'/'postgres.log'),'-o',f'-h 127.0.0.1 -p {config["port"]}','-w','start'],check=True,creationflags=subprocess.CREATE_NO_WINDOW)
with psycopg.connect(host='127.0.0.1',port=config['port'],user='urban_admin',password=config['admin_password'],dbname='postgres',autocommit=True) as conn:
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname='urban_app'").fetchone():
        conn.execute(sql.SQL('CREATE ROLE urban_app LOGIN PASSWORD {}').format(sql.Literal(config['app_password'])))
    if not conn.execute("SELECT 1 FROM pg_database WHERE datname='urban_furniture'").fetchone():
        conn.execute('CREATE DATABASE urban_furniture OWNER urban_app')
url=f'postgresql://urban_app:{config["app_password"]}@127.0.0.1:{config["port"]}/urban_furniture?sslmode=disable'
(root/'data'/'native-database-url').write_text(url,encoding='utf-8')
env_path=root/'.env'
if not env_path.exists():
    env_path.write_text('DATABASE_URL='+url+'\n',encoding='utf-8')
print('Native PostgreSQL is ready on 127.0.0.1:'+str(config['port']))
