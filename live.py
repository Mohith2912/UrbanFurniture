"""Live updates, operational insights, expenses, imports and payment approvals."""
import csv
import io
import json
import sqlite3
import time
from contextlib import closing
from datetime import date, timedelta
from decimal import Decimal

from flask import g, jsonify, request, Response
from database import connect, is_postgres, postgres_schema


def migrate(conn):
    postgres=getattr(conn,'dialect','')=='postgres'
    schema='''
    CREATE TABLE IF NOT EXISTS sync_state(id INTEGER PRIMARY KEY CHECK(id=1),revision INTEGER NOT NULL DEFAULT 0);
    INSERT OR IGNORE INTO sync_state(id,revision) VALUES(1,0);
    CREATE TABLE IF NOT EXISTS workspace(key TEXT PRIMARY KEY,value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS expenses(id INTEGER PRIMARY KEY,number TEXT UNIQUE,date TEXT NOT NULL,name TEXT NOT NULL,account_id INTEGER NOT NULL REFERENCES accounts(id),analytic_id INTEGER REFERENCES analytics(id),method TEXT NOT NULL,amount INTEGER NOT NULL,reference TEXT NOT NULL,entry_id INTEGER NOT NULL REFERENCES entries(id),created_by INTEGER NOT NULL REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS payment_requests(id INTEGER PRIMARY KEY,document_id INTEGER NOT NULL REFERENCES documents(id),date TEXT NOT NULL,method TEXT NOT NULL,amount INTEGER NOT NULL,reference TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_by INTEGER NOT NULL REFERENCES users(id),created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,reviewed_by INTEGER REFERENCES users(id),reviewed_at TEXT,review_note TEXT NOT NULL DEFAULT '',payment_id INTEGER REFERENCES payments(id));
    '''
    conn.executescript(postgres_schema(schema) if postgres else schema)
    upgrades={
        'products':[('sku',"TEXT NOT NULL DEFAULT ''"),('reorder_level','REAL NOT NULL DEFAULT 5'),('hsn',"TEXT NOT NULL DEFAULT ''"),('unit',"TEXT NOT NULL DEFAULT 'Nos'")],
        'contacts':[('gstin',"TEXT NOT NULL DEFAULT ''")],
        'orders':[('tax_mode',"TEXT NOT NULL DEFAULT 'intra'"),('place_of_supply',"TEXT NOT NULL DEFAULT ''"),('cgst','INTEGER NOT NULL DEFAULT 0'),('sgst','INTEGER NOT NULL DEFAULT 0'),('igst','INTEGER NOT NULL DEFAULT 0')],
        'order_lines':[('cgst','INTEGER NOT NULL DEFAULT 0'),('sgst','INTEGER NOT NULL DEFAULT 0'),('igst','INTEGER NOT NULL DEFAULT 0'),('hsn',"TEXT NOT NULL DEFAULT ''"),('unit',"TEXT NOT NULL DEFAULT 'Nos'")],
        'documents':[('seller_snapshot',"TEXT NOT NULL DEFAULT '{}'"),('buyer_snapshot',"TEXT NOT NULL DEFAULT '{}'")],
    }
    for table,fields in upgrades.items():
        columns={r[0] for r in conn.execute('SELECT column_name FROM information_schema.columns WHERE table_name=? AND table_schema=current_schema()',(table,))} if postgres else {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        for name,definition in fields:
            if name not in columns:
                if postgres:definition=definition.replace('INTEGER','BIGINT').replace('REAL','DOUBLE PRECISION')
                conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
    conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS product_sku ON products(sku) WHERE sku!=''")
    defaults=dict(company_name='Urban Furniture',email='',phone='',address='',tax_id='',state='',state_code='',bank_name='',account_number='',ifsc='',invoice_note='Thank you for your business.',default_terms='30')
    conn.executemany('INSERT OR IGNORE INTO workspace(key,value) VALUES(?,?)',defaults.items())
    if postgres:
        conn.execute('''CREATE OR REPLACE FUNCTION bump_live_revision() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN UPDATE sync_state SET revision=revision+1 WHERE id=1; RETURN NULL; END; $$''')
    for table in ['users','contacts','products','accounts','journals','analytics','budgets','orders','order_lines','documents','entries','entry_lines','payments','stock_moves','audit','workspace','expenses','payment_requests']:
        if postgres:
            conn.execute(f'CREATE OR REPLACE TRIGGER live_{table} AFTER INSERT OR UPDATE OR DELETE ON {table} FOR EACH STATEMENT EXECUTE FUNCTION bump_live_revision()')
            continue
        for event in ('INSERT','UPDATE','DELETE'):
            conn.execute(f'CREATE TRIGGER IF NOT EXISTS live_{table}_{event.lower()} AFTER {event} ON {table} BEGIN UPDATE sync_state SET revision=revision+1 WHERE id=1; END')
    conn.commit()
    if conn.execute('SELECT COUNT(*) FROM accounts').fetchone()[0]:
        ensure_tax_accounts(conn)


def ensure_tax_accounts(conn):
    for code,name,kind,key in [('1210','Input CGST','Asset','cgst_input'),('1220','Input SGST','Asset','sgst_input'),('1230','Input IGST','Asset','igst_input'),('2110','Output CGST','Liability','cgst_output'),('2120','Output SGST','Liability','sgst_output'),('2130','Output IGST','Liability','igst_output')]:
        conn.execute('INSERT OR IGNORE INTO accounts(code,name,type,system_key) VALUES(?,?,?,?)',(code,name,kind,key))
    conn.commit()


def workspace_data(conn):
    return {row['key']:row['value'] for row in conn.execute('SELECT key,value FROM workspace')}


def request_rows(conn, contact_id=None):
    sql='''SELECT r.*,d.number AS document_number,d.total-d.paid AS outstanding,c.name AS contact_name
           FROM payment_requests r JOIN documents d ON d.id=r.document_id JOIN contacts c ON c.id=d.contact_id'''
    return [dict(r) for r in conn.execute(sql+(' WHERE d.contact_id=?' if contact_id is not None else '')+' ORDER BY r.id DESC',(contact_id,) if contact_id is not None else ())]


def register_features(app, db, roles):
    # Imported after the application module has initialized to avoid circular initialization.
    from app import require, text_value, valid_date, money, decimal_value, rows, record, insert, audit, add_entry, line, account_key, validate_master, register_payment

    @app.get('/api/events')
    def events():
        user_id=g.user['id']; database=app.config['DATABASE']
        def stream():
            previous=None; heartbeat=time.monotonic(); started=heartbeat
            while time.monotonic()-started < 3600:
                # Release the connection on every iteration; never hold a read transaction open.
                with closing(connect(database)) as conn:
                    active=conn.execute('SELECT active FROM users WHERE id=?',(user_id,)).fetchone()
                    if not active or not active[0]:
                        yield 'event: revoked\ndata: {}\n\n'
                        return
                    revision=conn.execute('SELECT revision FROM sync_state WHERE id=1').fetchone()[0]
                if revision!=previous:
                    yield f'id: {revision}\nevent: change\ndata: '+json.dumps(dict(revision=revision))+'\n\n'
                    previous=revision
                elif time.monotonic()-heartbeat>=10:
                    yield ': heartbeat\n\n'; heartbeat=time.monotonic()
                time.sleep(2 if is_postgres(database) else .75)
        return Response(stream(),mimetype='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})

    @app.get('/api/sync')
    def sync():
        return jsonify(revision=db().execute('SELECT revision FROM sync_state WHERE id=1').fetchone()[0])

    @app.patch('/api/workspace')
    @roles('admin')
    def update_workspace():
        data=request.get_json()
        allowed={'company_name','email','phone','address','tax_id','invoice_note','default_terms','state','state_code','bank_name','account_number','ifsc'}
        require(set(data)<=allowed,'Unknown workspace setting.')
        values={key:text_value(data,key,key=='company_name',2000 if key in ('address','invoice_note') else 250) for key in data}
        if values.get('email'):
            require('@' in values['email'],'Enter a valid business email.')
        if values.get('tax_id'):
            require(len(values['tax_id'])==15 and values['tax_id'].isalnum(),'GSTIN must be 15 letters and digits.')
        if 'default_terms' in values:
            require(values['default_terms'].isdigit() and 0<=int(values['default_terms'])<=365,'Payment terms must be 0 to 365 days.')
        with db():
            db().executemany('INSERT INTO workspace(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',values.items())
            audit(db(),g.user['id'],'Business profile updated','workspace',None)
        return jsonify(ok=True)

    @app.get('/api/insights')
    @roles('admin','accountant')
    def insights():
        conn=db(); today=date.today(); end=(today+timedelta(days=30)).isoformat()
        open_docs=rows(conn,'''SELECT d.*,c.name AS contact_name FROM documents d JOIN contacts c ON c.id=d.contact_id
                         WHERE d.paid<d.total ORDER BY d.due_date,d.id''')
        aging={key:{'sale':0,'purchase':0} for key in ['current','1–30 days','31–60 days','61–90 days','90+ days']}
        for item in open_docs:
            days=(today-date.fromisoformat(item['due_date'])).days
            item['days_overdue']=max(days,0);item['outstanding']=item['total']-item['paid']
            key='current' if days<=0 else '1–30 days' if days<=30 else '31–60 days' if days<=60 else '61–90 days' if days<=90 else '90+ days'
            aging[key][item['kind']]+=item['outstanding']
        stock=rows(conn,"""SELECT p.*,COALESCE(SUM(CASE WHEN s.date<=? THEN s.quantity ELSE 0 END),0) AS quantity
                           FROM products p LEFT JOIN stock_moves s ON s.product_id=p.id WHERE p.type!='Service' AND p.active=1 GROUP BY p.id""",(today.isoformat(),))
        low=[p for p in stock if p['quantity']<=p['reorder_level']]
        cash=conn.execute("""SELECT COALESCE(SUM(l.debit-l.credit),0) FROM entry_lines l JOIN entries e ON e.id=l.entry_id
                           JOIN accounts a ON a.id=l.account_id WHERE a.system_key IN ('cash','bank') AND e.date<=?""",(today.isoformat(),)).fetchone()[0]
        incoming=sum(d['outstanding'] for d in open_docs if d['kind']=='sale' and d['due_date']<=end)
        outgoing=sum(d['outstanding'] for d in open_docs if d['kind']=='purchase' and d['due_date']<=end)
        trend=rows(conn,"""SELECT substr(e.date,1,7) AS month,
                        SUM(CASE WHEN a.type='Income' THEN l.credit-l.debit ELSE 0 END) AS income,
                        SUM(CASE WHEN a.type='Expense' THEN l.debit-l.credit ELSE 0 END) AS expense
                        FROM entry_lines l JOIN entries e ON e.id=l.entry_id JOIN accounts a ON a.id=l.account_id
                        WHERE e.date BETWEEN ? AND ? GROUP BY month ORDER BY month""",((today.replace(day=1)-timedelta(days=155)).replace(day=1).isoformat(),today.isoformat()))
        totals={kind:sum(d['outstanding'] for d in open_docs if d['kind']==kind) for kind in ('sale','purchase')}
        onboarding=dict(profile=bool(workspace_data(conn).get('address')),contacts=conn.execute('SELECT COUNT(*) FROM contacts WHERE active=1').fetchone()[0]>0,products=conn.execute('SELECT COUNT(*) FROM products WHERE active=1').fetchone()[0]>0,purchase=conn.execute("SELECT COUNT(*) FROM documents WHERE kind='purchase'").fetchone()[0]>0,sale=conn.execute("SELECT COUNT(*) FROM documents WHERE kind='sale'").fetchone()[0]>0)
        return jsonify(open_documents=open_docs,aging=aging,low_stock=low,cash=cash,incoming=incoming,outgoing=outgoing,projected_cash=cash+incoming-outgoing,totals=totals,trend=trend,onboarding=onboarding,pending_requests=conn.execute("SELECT COUNT(*) FROM payment_requests WHERE status='pending'").fetchone()[0],as_of=today.isoformat())

    @app.post('/api/expenses')
    @roles('admin','accountant')
    def create_expense():
        data=request.get_json(); conn=db(); amount=money(data.get('amount'))
        require(amount>0,'Expense amount must be positive.')
        account=record(conn,'accounts',data.get('account_id'),True);require(account['type']=='Expense','Select an expense account.')
        method=data.get('method');require(method in ('Cash','Bank'),'Select Cash or Bank.')
        analytic_id=data.get('analytic_id') or None
        if analytic_id:
            require(record(conn,'analytics',analytic_id,True)['type']=='Expense','Select an expense analytic account.')
        when=valid_date(data.get('date')); name=text_value(data,'name');reference=text_value(data,'reference',False)
        journal=conn.execute('SELECT id FROM journals WHERE type=? AND active=1 ORDER BY id LIMIT 1',(method,)).fetchone()
        require(journal is not None,'An active payment journal is required.')
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            entry_id=add_entry(conn,g.user['id'],journal['id'],when,name,'expense',None,[line(account['id'],debit=amount,analytic=analytic_id),line(account_key(conn,method.lower()),credit=amount)])
            eid=insert(conn,'expenses',dict(date=when,name=name,account_id=account['id'],analytic_id=analytic_id,method=method,amount=amount,reference=reference,entry_id=entry_id,created_by=g.user['id']))
            conn.execute('UPDATE expenses SET number=? WHERE id=?',(f'EXP-{eid:05}',eid))
            conn.execute('UPDATE entries SET source_id=? WHERE id=?',(eid,entry_id))
            audit(conn,g.user['id'],'Expense recorded','expenses',eid,name)
        return jsonify(id=eid),201

    @app.post('/api/payment-requests')
    @roles('contact')
    def submit_payment():
        data=request.get_json();conn=db()
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            doc=record(conn,'documents',data.get('document_id'))
            require(doc['contact_id']==g.user['contact_id'] and doc['kind']=='sale','You may submit payment only for your own customer invoice.')
            amount=money(data.get('amount'));when=valid_date(data.get('date'))
            require(doc['date']<=when<=date.today().isoformat(),'Use a payment date from the invoice date through today.')
            require(data.get('method') in ('Cash','Bank'),'Select Cash or Bank.')
            reserved=conn.execute("SELECT COALESCE(SUM(amount),0) FROM payment_requests WHERE document_id=? AND status='pending'",(doc['id'],)).fetchone()[0]
            require(0<amount<=doc['total']-doc['paid']-reserved,'Amount exceeds the balance available after pending payment requests.')
            rid=insert(conn,'payment_requests',dict(document_id=doc['id'],date=when,method=data['method'],amount=amount,reference=text_value(data,'reference'),created_by=g.user['id']))
            audit(conn,g.user['id'],'Payment submitted for review','payment_requests',rid,doc['number'])
        return jsonify(id=rid),201

    @app.post('/api/payment-requests/<int:identifier>/review')
    @roles('admin','accountant')
    def review_payment(identifier):
        data=request.get_json();decision=data.get('decision');require(decision in ('approved','rejected'),'Choose approve or reject.')
        conn=db()
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            payment=record(conn,'payment_requests',identifier);require(payment['status']=='pending','This request has already been reviewed.')
            note=text_value(data,'note',decision=='rejected',1000);pid=None
            if decision=='approved':
                pid=register_payment(conn,payment['document_id'],dict(date=payment['date'],method=payment['method'],amount=str(Decimal(payment['amount'])/100),reference=payment['reference']),g.user)
            conn.execute("UPDATE payment_requests SET status=?,reviewed_by=?,reviewed_at=CURRENT_TIMESTAMP,review_note=?,payment_id=? WHERE id=?",(decision,g.user['id'],note,pid,identifier))
            audit(conn,g.user['id'],'Payment '+decision,'payment_requests',identifier,note)
        return jsonify(ok=True,payment_id=pid)

    @app.get('/api/contacts/<int:identifier>/statement')
    def statement(identifier):
        if g.user['role']=='contact' and g.user['contact_id']!=identifier:
            return jsonify(error='Access denied.'),403
        conn=db();contact=record(conn,'contacts',identifier)
        start=valid_date(request.args.get('start','2000-01-01'));end=valid_date(request.args.get('end',date.today().isoformat()));require(start<=end,'Choose a valid period.')
        opening=conn.execute('''SELECT COALESCE(SUM(l.debit-l.credit),0) FROM entry_lines l JOIN entries e ON e.id=l.entry_id WHERE l.contact_id=? AND e.date<?''',(identifier,start)).fetchone()[0]
        movements=rows(conn,'''SELECT e.date,e.number,e.reference,l.debit,l.credit FROM entry_lines l JOIN entries e ON e.id=l.entry_id WHERE l.contact_id=? AND e.date BETWEEN ? AND ? ORDER BY e.date,e.id,l.id''',(identifier,start,end))
        balance=opening
        for movement in movements:
            balance+=movement['debit']-movement['credit'];movement['balance']=balance
        return jsonify(contact=contact,start=start,end=end,opening=opening,closing=balance,movements=movements)

    @app.post('/api/import/<table>')
    @roles('admin','accountant')
    def import_csv(table):
        require(table in ('contacts','products'),'Import supports contacts or products.')
        data=request.get_json();source=text_value(data,'csv',True,500000).lstrip('\ufeff')
        reader=csv.DictReader(io.StringIO(source))
        fields={'contacts':{'name','type','email','mobile','city','state','pincode','address','gstin'},'products':{'name','type','sales_price','cost','category','sku','reorder_level','hsn','unit'}}[table]
        required={'name','type'} if table=='contacts' else {'name','type','sales_price','cost'}
        require(reader.fieldnames is not None and required<=set(reader.fieldnames),'CSV is missing required columns: '+', '.join(sorted(required)))
        require(set(reader.fieldnames)<=fields,'CSV has unsupported columns. Use the downloadable template.')
        prepared=[];errors=[];seen=set();conn=db()
        existing={str(r[0]).casefold() for r in conn.execute(f'SELECT name FROM {table}')}
        for row_number,item in enumerate(reader,start=2):
            require(row_number<=501,'Import at most 500 records at a time.')
            try:
                require(None not in item,'Row has too many columns.')
                values=validate_master(conn,table,item)
                key=values['name'].casefold()
                require(key not in seen and key not in existing,'Name already exists in this file or workspace.')
                if table=='products' and values.get('sku'):
                    require(not conn.execute('SELECT 1 FROM products WHERE sku=?',(values['sku'],)).fetchone(),'SKU already exists.')
                    require(not any(v.get('sku')==values['sku'] for v in prepared),'SKU is duplicated in this file.')
                seen.add(key);prepared.append(values)
            except Exception as error:
                from app import ValidationError
                if not isinstance(error,ValidationError):raise
                errors.append(dict(row=row_number,message=str(error)))
        require(row_number if 'row_number' in locals() else False,'CSV contains no rows.')
        if not data.get('commit'):
            return jsonify(count=len(prepared),rows=prepared[:20],errors=errors,valid=not errors)
        require(not errors,'Fix the CSV errors before importing. '+(errors[0]['message'] if errors else ''))
        with conn:
            for values in prepared:insert(conn,table,values)
            audit(conn,g.user['id'],'CSV imported',table,None,f'{len(prepared)} records')
        return jsonify(count=len(prepared)),201

    @app.get('/api/import/<table>/template')
    @roles('admin','accountant')
    def import_template(table):
        require(table in ('contacts','products'),'Unknown template.')
        fields='name,type,email,mobile,city,state,pincode,address' if table=='contacts' else 'name,type,sales_price,cost,category,sku,reorder_level'
        return Response(fields+'\r\n',mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename={table}-template.csv'})
