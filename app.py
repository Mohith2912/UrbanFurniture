"""Urban Furniture: transactional accounting application. Amounts are integer paise."""
import csv
import io
import json
import os
import secrets
import sqlite3
import time
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from functools import wraps
from contextlib import closing
from pathlib import Path

from flask import Flask, g, jsonify, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash
from database import connect, is_postgres, postgres_schema, load_env, database_label
from live import migrate, register_features, workspace_data, request_rows, ensure_tax_accounts

ROOT = Path(__file__).resolve().parent
SCHEMA = """
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,name TEXT NOT NULL,email TEXT NOT NULL UNIQUE COLLATE NOCASE,password TEXT NOT NULL,role TEXT NOT NULL CHECK(role IN ('admin','accountant','contact')),contact_id INTEGER REFERENCES contacts(id),active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS contacts(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,email TEXT NOT NULL DEFAULT '',mobile TEXT NOT NULL DEFAULT '',city TEXT NOT NULL DEFAULT '',state TEXT NOT NULL DEFAULT '',pincode TEXT NOT NULL DEFAULT '',address TEXT NOT NULL DEFAULT '',image TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,sales_price INTEGER NOT NULL,cost INTEGER NOT NULL,category TEXT NOT NULL DEFAULT '',active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS accounts(id INTEGER PRIMARY KEY,code TEXT NOT NULL UNIQUE,name TEXT NOT NULL,type TEXT NOT NULL,system_key TEXT UNIQUE,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS journals(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,debit_account_id INTEGER NOT NULL REFERENCES accounts(id),credit_account_id INTEGER NOT NULL REFERENCES accounts(id),active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS analytics(id INTEGER PRIMARY KEY,name TEXT NOT NULL,type TEXT NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS budgets(id INTEGER PRIMARY KEY,name TEXT NOT NULL,start_date TEXT NOT NULL,end_date TEXT NOT NULL,responsible TEXT NOT NULL,analytic_id INTEGER NOT NULL REFERENCES analytics(id),planned INTEGER NOT NULL,active INTEGER NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,number TEXT UNIQUE,kind TEXT NOT NULL,contact_id INTEGER NOT NULL REFERENCES contacts(id),date TEXT NOT NULL,due_date TEXT NOT NULL,journal_id INTEGER NOT NULL REFERENCES journals(id),analytic_id INTEGER REFERENCES analytics(id),notes TEXT NOT NULL DEFAULT '',status TEXT NOT NULL DEFAULT 'draft',subtotal INTEGER NOT NULL,tax INTEGER NOT NULL,total INTEGER NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS order_lines(id INTEGER PRIMARY KEY,order_id INTEGER NOT NULL REFERENCES orders(id),product_id INTEGER NOT NULL REFERENCES products(id),description TEXT NOT NULL,product_type TEXT NOT NULL,quantity TEXT NOT NULL,unit_price INTEGER NOT NULL,tax_rate TEXT NOT NULL,subtotal INTEGER NOT NULL,tax INTEGER NOT NULL,total INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS documents(id INTEGER PRIMARY KEY,number TEXT UNIQUE,order_id INTEGER NOT NULL UNIQUE REFERENCES orders(id),kind TEXT NOT NULL,contact_id INTEGER NOT NULL REFERENCES contacts(id),date TEXT NOT NULL,due_date TEXT NOT NULL,total INTEGER NOT NULL,paid INTEGER NOT NULL DEFAULT 0,created_by INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS entries(id INTEGER PRIMARY KEY,number TEXT UNIQUE,date TEXT NOT NULL,journal_id INTEGER NOT NULL REFERENCES journals(id),reference TEXT NOT NULL,source TEXT NOT NULL,source_id INTEGER,created_by INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS entry_lines(id INTEGER PRIMARY KEY,entry_id INTEGER NOT NULL REFERENCES entries(id),account_id INTEGER NOT NULL REFERENCES accounts(id),contact_id INTEGER REFERENCES contacts(id),analytic_id INTEGER REFERENCES analytics(id),debit INTEGER NOT NULL DEFAULT 0,credit INTEGER NOT NULL DEFAULT 0,CHECK(debit>=0 AND credit>=0 AND NOT(debit>0 AND credit>0)));
CREATE TABLE IF NOT EXISTS payments(id INTEGER PRIMARY KEY,number TEXT UNIQUE,document_id INTEGER NOT NULL REFERENCES documents(id),date TEXT NOT NULL,method TEXT NOT NULL,amount INTEGER NOT NULL,reference TEXT NOT NULL,created_by INTEGER NOT NULL REFERENCES users(id));
CREATE TABLE IF NOT EXISTS stock_moves(id INTEGER PRIMARY KEY,product_id INTEGER NOT NULL REFERENCES products(id),document_id INTEGER NOT NULL REFERENCES documents(id),date TEXT NOT NULL,quantity REAL NOT NULL);
CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY,created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,user_id INTEGER REFERENCES users(id),action TEXT NOT NULL,entity TEXT NOT NULL,entity_id INTEGER,detail TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS entry_date ON entries(date);
CREATE INDEX IF NOT EXISTS stock_product ON stock_moves(product_id,date);
CREATE INDEX IF NOT EXISTS document_contact ON documents(contact_id);
"""


class ValidationError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise ValidationError(message)


def text_value(data, key, required=True, maximum=250):
    raw = data.get(key, '')
    require(isinstance(raw, str), f'{key.replace("_", " ").capitalize()} must be text.')
    value = raw.strip()
    require(not required or bool(value), f'{key.replace("_", " ").capitalize()} is required.')
    require(len(value) <= maximum, f'{key} is too long.')
    return value


def decimal_value(value, label, minimum=Decimal(0), maximum=Decimal('1000000000')):
    require(len(str(value)) <= 40, f'{label} is too long.')
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValidationError(f'{label} must be a number.')
    require(result.is_finite() and minimum <= result <= maximum, f'{label} must be between {minimum} and {maximum}.')
    return result


def money(value, label='Amount'):
    return int((decimal_value(value, label) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def valid_date(value):
    try:
        parsed = date.fromisoformat(str(value))
        require(parsed.isoformat() == value, 'Use dates in YYYY-MM-DD format.')
        return parsed.isoformat()
    except (ValueError, TypeError):
        raise ValidationError('Enter a valid date in YYYY-MM-DD format.')


def rows(db, sql, params=()):
    return [dict(row) for row in db.execute(sql, params).fetchall()]


def record(db, table, identifier, active=False):
    require(str(identifier).isdigit(), 'Select a valid record.')
    row = db.execute(f'SELECT * FROM {table} WHERE id=?', (identifier,)).fetchone()
    require(row is not None, f'{table.capitalize()} record not found.')
    if active:
        require(row['active'], f'This {table} record is archived.')
    return dict(row)


def insert(db, table, values):
    columns = ','.join(values)
    marks = ','.join('?' for _ in values)
    sql=f'INSERT INTO {table} ({columns}) VALUES ({marks})'
    if getattr(db,'dialect','')=='postgres':
        return db.execute(sql+' RETURNING id',tuple(values.values())).fetchone()[0]
    return db.execute(sql, tuple(values.values())).lastrowid


def audit(db, user_id, action, entity, identifier, detail=''):
    insert(db, 'audit', dict(user_id=user_id, action=action, entity=entity, entity_id=identifier, detail=detail))


def account_key(db, key):
    return db.execute('SELECT id FROM accounts WHERE system_key=?', (key,)).fetchone()['id']


def add_entry(db, user_id, journal_id, when, reference, source, source_id, lines):
    require(len(lines) >= 2, 'A journal entry needs at least two lines.')
    require(sum(x['debit'] for x in lines) == sum(x['credit'] for x in lines), 'Debits and credits must balance exactly.')
    require(sum(x['debit'] for x in lines) > 0, 'A journal entry must have a positive amount.')
    identifier = insert(db, 'entries', dict(date=when, journal_id=journal_id, reference=reference, source=source, source_id=source_id, created_by=user_id))
    db.execute('UPDATE entries SET number=? WHERE id=?', (f'JE-{identifier:05}', identifier))
    for line in lines:
        insert(db, 'entry_lines', dict(entry_id=identifier, **line))
    return identifier


def line(account, debit=0, credit=0, contact=None, analytic=None):
    return dict(account_id=account, debit=debit, credit=credit, contact_id=contact, analytic_id=analytic)


def create_order(db, data, user_id):
    kind = data.get('kind')
    require(kind in ('sale', 'purchase'), 'Invalid order type.')
    contact = record(db, 'contacts', data.get('contact_id'), True)
    require(contact['type'] in (('Customer', 'Both') if kind == 'sale' else ('Vendor', 'Both')), 'Contact type does not match this order.')
    journal = record(db, 'journals', data.get('journal_id'), True)
    require(journal['type'] == ('Sales' if kind == 'sale' else 'Purchase'), 'Select the appropriate sales or purchase journal.')
    when, due = valid_date(data.get('date')), valid_date(data.get('due_date'))
    require(due >= when, 'Due date cannot precede the order date.')
    tax_mode=data.get('tax_mode','intra')
    require(tax_mode in ('intra','inter','exempt'),'Choose CGST + SGST, IGST, or tax exempt.')
    place_of_supply=text_value(data,'place_of_supply',False,150) or contact['state']
    analytic_id = data.get('analytic_id') or None
    if analytic_id:
        analytic = record(db, 'analytics', analytic_id, True)
        require(analytic['type'] == ('Income' if kind == 'sale' else 'Expense'), 'Analytic account must match the transaction type.')
    items = data.get('lines', [])
    require(isinstance(items, list) and 0 < len(items) <= 100, 'Add between 1 and 100 product lines.')
    prepared = []
    for item in items:
        require(isinstance(item, dict), 'Each order line must be an object.')
        product = record(db, 'products', item.get('product_id'), True)
        qty = decimal_value(item.get('quantity'), 'Quantity', Decimal('0.001'), Decimal('1000000'))
        require(qty.as_tuple().exponent >= -3, 'Quantity supports up to 3 decimal places.')
        price = money(item.get('unit_price'), 'Unit price')
        rate = decimal_value(item.get('tax_rate', 0), 'Tax rate', maximum=Decimal(100))
        if tax_mode=='exempt':rate=Decimal(0)
        subtotal = int((qty * price).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        tax = int((subtotal * rate / 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
        cgst=int((Decimal(tax)/2).quantize(Decimal(1),rounding=ROUND_HALF_UP)) if tax_mode=='intra' else 0
        sgst=tax-cgst if tax_mode=='intra' else 0
        igst=tax if tax_mode=='inter' else 0
        prepared.append(dict(product_id=product['id'], description=product['name'], product_type=product['type'], quantity=str(qty), unit_price=price, tax_rate=str(rate), subtotal=subtotal, tax=tax, total=subtotal+tax,cgst=cgst,sgst=sgst,igst=igst,hsn=product.get('hsn',''),unit=product.get('unit','Nos')))
    subtotal, tax = sum(x['subtotal'] for x in prepared), sum(x['tax'] for x in prepared)
    require(0 < subtotal + tax <= 100_000_000_000, 'Order total must be positive and at most INR 1 billion.')
    identifier = insert(db, 'orders', dict(kind=kind, contact_id=contact['id'], date=when, due_date=due, journal_id=journal['id'], analytic_id=analytic_id, notes=text_value(data, 'notes', False, 2000), subtotal=subtotal, tax=tax, total=subtotal+tax, created_by=user_id,tax_mode=tax_mode,place_of_supply=place_of_supply,cgst=sum(x['cgst'] for x in prepared),sgst=sum(x['sgst'] for x in prepared),igst=sum(x['igst'] for x in prepared)))
    db.execute('UPDATE orders SET number=? WHERE id=?', (f'{"SO" if kind == "sale" else "PO"}-{identifier:05}', identifier))
    for item in prepared:
        insert(db, 'order_lines', dict(order_id=identifier, **item))
    audit(db, user_id, 'Created', 'orders', identifier)
    return identifier


def post_order(db, identifier, data, user_id):
    order = record(db, 'orders', identifier)
    require(order['status'] == 'draft', 'Only a draft order can be converted, and only once.')
    when = valid_date(data.get('date', order['date']))
    due = valid_date(data.get('due_date', order['due_date']))
    require(when >= order['date'] and due >= when, 'Invoice date must follow the order date; due date must follow the invoice date.')
    journal = record(db, 'journals', order['journal_id'], True)
    record(db, 'accounts', journal['debit_account_id'], True)
    record(db, 'accounts', journal['credit_account_id'], True)
    record(db, 'contacts', order['contact_id'], True)
    if order['analytic_id']:
        record(db, 'analytics', order['analytic_id'], True)
    sale = order['kind'] == 'sale'
    items = rows(db, 'SELECT * FROM order_lines WHERE order_id=?', (identifier,))
    # Aggregate repeated product lines before checking availability.
    quantities = {}
    for item in items:
        record(db, 'products', item['product_id'], True)
        if item['product_type'] != 'Service':
            quantities[item['product_id']] = quantities.get(item['product_id'], Decimal(0)) + Decimal(item['quantity'])
    if sale:
        for product_id, qty in quantities.items():
            available = db.execute('SELECT COALESCE(SUM(quantity),0) FROM stock_moves WHERE product_id=? AND date<=?', (product_id, when)).fetchone()[0]
            require(Decimal(str(available)) + Decimal('0.000001') >= qty, 'Insufficient stock on the invoice date. Post a vendor bill first.')
            # Backdating must not make a subsequent day's historical stock negative.
            future = rows(db, 'SELECT date,SUM(quantity) AS qty FROM stock_moves WHERE product_id=? AND date>? GROUP BY date ORDER BY date', (product_id, when))
            balance = Decimal(str(available)) - qty
            for movement in future:
                balance += Decimal(str(movement['qty']))
                require(balance >= Decimal('-0.000001'), 'This backdated sale would make historical stock negative.')
    seller=workspace_data(db);buyer=record(db,'contacts',order['contact_id']);buyer.pop('image',None)
    doc_id = insert(db, 'documents', dict(order_id=identifier, kind=order['kind'], contact_id=order['contact_id'], date=when, due_date=due, total=order['total'], created_by=user_id,seller_snapshot=json.dumps(seller),buyer_snapshot=json.dumps(buyer)))
    number = f'{"INV" if sale else "BILL"}-{doc_id:05}'
    db.execute('UPDATE documents SET number=? WHERE id=?', (number, doc_id))
    contact, analytic = order['contact_id'], order['analytic_id']
    if sale:
        posting = [line(journal['debit_account_id'], debit=order['total'], contact=contact), line(journal['credit_account_id'], credit=order['subtotal'], analytic=analytic)]
        for component in ('cgst','sgst','igst'):
            if order[component]:posting.append(line(account_key(db,component+'_output'),credit=order[component]))
        if order['tax'] and not (order['cgst']+order['sgst']+order['igst']):posting.append(line(account_key(db,'tax_output'),credit=order['tax']))
    else:
        posting = [line(journal['debit_account_id'], debit=order['subtotal'], analytic=analytic), line(journal['credit_account_id'], credit=order['total'], contact=contact)]
        for component in ('cgst','sgst','igst'):
            if order[component]:posting.append(line(account_key(db,component+'_input'),debit=order[component]))
        if order['tax'] and not (order['cgst']+order['sgst']+order['igst']):posting.append(line(account_key(db,'tax_input'),debit=order['tax']))
    add_entry(db, user_id, journal['id'], when, number, 'document', doc_id, posting)
    for product_id, qty in quantities.items():
        insert(db, 'stock_moves', dict(product_id=product_id, document_id=doc_id, date=when, quantity=float(-qty if sale else qty)))
    db.execute("UPDATE orders SET status='posted' WHERE id=?", (identifier,))
    audit(db, user_id, 'Posted', 'documents', doc_id, number)
    return doc_id


def register_payment(db, identifier, data, user):
    doc = record(db, 'documents', identifier)
    if user['role'] == 'contact':
        require(doc['contact_id'] == user['contact_id'] and doc['kind'] == 'sale', 'You can only pay your own customer invoices.')
    amount = money(data.get('amount'))
    require(0 < amount <= doc['total'] - doc['paid'], 'Payment must be positive and cannot exceed the outstanding balance.')
    when = valid_date(data.get('date'))
    require(when >= doc['date'], 'Payment date cannot precede the invoice date.')
    method = data.get('method')
    require(method in ('Cash', 'Bank'), 'Select Cash or Bank.')
    journal = db.execute('SELECT * FROM journals WHERE type=? AND active=1 ORDER BY id LIMIT 1', (method,)).fetchone()
    require(journal is not None, f'An active {method} journal is required.')
    reference = text_value(data, 'reference', False)
    payment_id = insert(db, 'payments', dict(document_id=identifier, date=when, method=method, amount=amount, reference=reference, created_by=user['id']))
    number = f'PAY-{payment_id:05}'
    db.execute('UPDATE payments SET number=? WHERE id=?', (number, payment_id))
    # Use the original posted control account even if the journal defaults later change.
    control = db.execute('SELECT l.account_id FROM entry_lines l JOIN entries e ON e.id=l.entry_id WHERE e.source=\'document\' AND e.source_id=? AND l.contact_id=?', (identifier, doc['contact_id'])).fetchone()['account_id']
    cash = journal['debit_account_id']
    if doc['kind'] == 'sale':
        posting = [line(cash, debit=amount), line(control, credit=amount, contact=doc['contact_id'])]
    else:
        posting = [line(control, debit=amount, contact=doc['contact_id']), line(cash, credit=amount)]
    add_entry(db, user['id'], journal['id'], when, f'{number} / {doc["number"]}', 'payment', payment_id, posting)
    db.execute('UPDATE documents SET paid=paid+? WHERE id=?', (amount, identifier))
    audit(db, user['id'], 'Payment recorded', 'documents', identifier, f'{number}: {amount} paise via {method}')
    return payment_id


def seed_core(db):
    for code, name, kind, key in [('1000','Cash','Asset','cash'),('1010','Bank','Asset','bank'),('1100','Accounts receivable','Asset','receivable'),('1200','Input tax','Asset','tax_input'),('2000','Accounts payable','Liability','payable'),('2100','Output tax','Liability','tax_output'),('3000','Owner capital','Capital','capital'),('4000','Furniture sales','Income','sales'),('5000','Purchases','Expense','purchases'),('5100','Operating expenses','Expense',None)]:
        insert(db, 'accounts', dict(code=code, name=name, type=kind, system_key=key))
    for name, kind, debit, credit in [('Customer sales','Sales','receivable','sales'),('Vendor purchases','Purchase','purchases','payable'),('Bank transactions','Bank','bank','receivable'),('Cash transactions','Cash','cash','receivable'),('General journal','General','purchases','bank')]:
        insert(db, 'journals', dict(name=name, type=kind, debit_account_id=account_key(db,debit), credit_account_id=account_key(db,credit)))


MASTER_FIELDS = {
    'contacts': ['name','type','email','mobile','city','state','pincode','address','image'],
    'products': ['name','type','sales_price','cost','category'],
    'accounts': ['name','code','type'],
    'journals': ['name','type','debit_account_id','credit_account_id'],
    'analytics': ['name','type'],
    'budgets': ['name','start_date','end_date','responsible','analytic_id','planned'],
}


def validate_master(db, table, data):
    result={'name':text_value(data,'name')}
    types={'contacts':['Customer','Vendor','Both'],'products':['Goods','Service','Combo'],'accounts':['Asset','Liability','Expense','Income','Capital'],'journals':['Sales','Purchase','Bank','Cash','General'],'analytics':['Income','Expense']}
    if table in types:
        require(data.get('type') in types[table], 'Select a valid type.')
        result['type']=data['type']
    if table=='contacts':
        for field in ['email','mobile','city','state','pincode','address']:
            result[field]=text_value(data,field,False,1000 if field=='address' else 250)
        require(not result['email'] or ('@' in result['email'] and '.' in result['email'].split('@')[-1]), 'Enter a valid email address.')
        image=data.get('image','')
        require(isinstance(image,str) and len(image)<700000, 'Profile image must be under 500 KB.')
        require(not image or image.startswith(('data:image/png;base64,','data:image/jpeg;base64,','data:image/webp;base64,')), 'Use a PNG, JPEG or WebP profile image.')
        result['image']=image
    if table=='products':
        result.update(sales_price=money(data.get('sales_price')),cost=money(data.get('cost')),category=text_value(data,'category',False))
        result.update(sku=text_value(data,'sku',False,40),reorder_level=float(decimal_value(data.get('reorder_level',5),'Reorder level',maximum=Decimal('1000000'))),hsn=text_value(data,'hsn',False,12),unit=text_value(data,'unit',False,20) or 'Nos')
    if table=='contacts':
        result['gstin']=text_value(data,'gstin',False,15).upper()
        require(not result['gstin'] or (len(result['gstin'])==15 and result['gstin'].isalnum()),'GSTIN must contain 15 letters and digits.')
    if table=='accounts':
        result['code']=text_value(data,'code',True,20)
    if table=='journals':
        debit=record(db,'accounts',data.get('debit_account_id'),True); credit=record(db,'accounts',data.get('credit_account_id'),True)
        require(debit['id'] != credit['id'], 'Default debit and credit accounts must differ.')
        if result['type']=='Sales':
            require(debit['system_key']=='receivable' and credit['type']=='Income', 'Sales journals require Accounts receivable and an Income account.')
        if result['type']=='Purchase':
            require(debit['type']=='Expense' and credit['system_key']=='payable', 'Purchase journals require an Expense account and Accounts payable.')
        if result['type'] in ('Cash','Bank'):
            require(debit['system_key']==result['type'].lower(), 'The debit default must be the matching Cash or Bank account.')
        result.update(debit_account_id=debit['id'],credit_account_id=credit['id'])
    if table=='budgets':
        result.update(start_date=valid_date(data.get('start_date')),end_date=valid_date(data.get('end_date')),responsible=text_value(data,'responsible'),planned=money(data.get('planned')),analytic_id=record(db,'analytics',data.get('analytic_id'),True)['id'])
        require(result['start_date']<=result['end_date'], 'Budget end date must follow its start date.')
    return result


def create_app(database=None, testing=False):
    app=Flask(__name__,static_folder='static')
    if not testing and not os.environ.get('VERCEL'):
        load_env(ROOT/'.env')
    if os.environ.get('VERCEL') and database is None and not os.environ.get('DATABASE_URL'):
        raise RuntimeError('DATABASE_URL is required for a Vercel deployment.')
    configured_database=database or os.environ.get('DATABASE_URL') or os.environ.get('URBAN_DB')
    target=str(configured_database or ROOT/'data'/'urban.sqlite3')
    folder=ROOT/'data' if is_postgres(target) else Path(target).parent
    configured_secret=os.environ.get('URBAN_SECRET')
    if os.environ.get('VERCEL') and not configured_secret:
        raise RuntimeError('URBAN_SECRET is required for a Vercel deployment.')
    if not configured_secret:
        folder.mkdir(parents=True,exist_ok=True)
        secret_path=folder/'.secret'
        if not secret_path.exists():
            secret_path.write_text(secrets.token_hex(32),encoding='utf-8')
        configured_secret=secret_path.read_text(encoding='utf-8')
    app.config.update(SECRET_KEY=configured_secret,DATABASE=target,TESTING=testing,SESSION_COOKIE_NAME=('urban_qa' if testing else 'session'),SESSION_COOKIE_HTTPONLY=True,SESSION_COOKIE_SAMESITE='Strict',SESSION_COOKIE_SECURE=os.environ.get('URBAN_HTTPS')=='1',PERMANENT_SESSION_LIFETIME=timedelta(hours=8),MAX_CONTENT_LENGTH=2*1024*1024)
    with closing(connect(target)) as conn:
        conn.executescript(postgres_schema(SCHEMA) if is_postgres(target) else SCHEMA)
        if not is_postgres(target):conn.execute('PRAGMA journal_mode=WAL')
        conn.commit()
        migrate(conn)
    attempts={}

    def db():
        if 'db' not in g:
            g.db=connect(app.config['DATABASE'])
        return g.db

    @app.teardown_appcontext
    def close(_):
        if 'db' in g:
            g.db.close()

    @app.before_request
    def protect():
        if request.path.startswith('/api/'):
            if request.method not in ('GET','HEAD','OPTIONS'):
                require(request.is_json, 'Send a JSON request.')
                require(isinstance(request.get_json(silent=True), dict), 'Send a valid JSON object.')
                if not secrets.compare_digest(str(request.headers.get('X-CSRF-Token','')),str(session.get('csrf','missing'))):
                    return jsonify(error='Your session expired. Refresh the page and try again.'),403
            if request.path not in ('/api/health','/api/session','/api/setup','/api/login'):
                user=db().execute('SELECT id,name,email,role,contact_id FROM users WHERE id=? AND active=1',(session.get('uid'),)).fetchone()
                if user is None:
                    return jsonify(error='Please sign in.'),401
                g.user=dict(user)

    @app.after_request
    def headers(response):
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['X-Frame-Options']='DENY'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'"
        if request.path.startswith('/api/'):
            response.headers['Cache-Control']='no-store'
        return response

    @app.errorhandler(ValidationError)
    def invalid(error):
        return jsonify(error=str(error)),400

    @app.errorhandler(sqlite3.IntegrityError)
    def conflict(error):
        return jsonify(error='This record conflicts with an existing record. Check unique codes and email addresses.'),409

    if is_postgres(target):
        import psycopg
        app.register_error_handler(psycopg.IntegrityError,conflict)

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error='Request is too large. Use a smaller profile image.'),413

    def roles(*allowed):
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args,**kwargs):
                if g.user['role'] not in allowed:
                    return jsonify(error='Your role does not allow this action.'),403
                return fn(*args,**kwargs)
            return wrapper
        return decorator

    @app.get('/')
    def index():
        return send_from_directory(app.static_folder,'index.html')

    @app.get('/api/health')
    def health():
        return jsonify(ok=True,service='urban-furniture-api')

    @app.get('/api/session')
    def status():
        session.setdefault('csrf',secrets.token_hex(32))
        user=db().execute('SELECT id,name,email,role,contact_id FROM users WHERE id=? AND active=1',(session.get('uid'),)).fetchone()
        return jsonify(csrf=session['csrf'],user=dict(user) if user else None,needs_setup=db().execute('SELECT COUNT(*) FROM users').fetchone()[0]==0)

    @app.post('/api/setup')
    def setup():
        data=request.get_json()
        name=text_value(data,'name'); email=text_value(data,'email').lower(); password=text_value(data,'password',True,200)
        require('@' in email, 'Enter a valid email.')
        require(len(password)>=10,'Use a password with at least 10 characters.')
        conn=db()
        with conn:
            conn.execute('BEGIN IMMEDIATE')
            require(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]==0,'Setup has already been completed.')
            uid=insert(conn,'users',dict(name=name,email=email,password=generate_password_hash(password),role='admin'))
            seed_core(conn)
            # Seed tax accounts within the same setup transaction.
            for code,name,kind,key in [('1210','Input CGST','Asset','cgst_input'),('1220','Input SGST','Asset','sgst_input'),('1230','Input IGST','Asset','igst_input'),('2110','Output CGST','Liability','cgst_output'),('2120','Output SGST','Liability','sgst_output'),('2130','Output IGST','Liability','igst_output')]:
                insert(conn,'accounts',dict(code=code,name=name,type=kind,system_key=key))
            audit(conn,uid,'Workspace created','system',None)
        session['uid']=uid; session.permanent=True
        return jsonify(ok=True)

    @app.post('/api/login')
    def login():
        data=request.get_json(); key=request.remote_addr; now=time.time()
        recent=[t for t in attempts.get(key,[]) if now-t<300]
        if len(recent)>=10:
            return jsonify(error='Too many attempts. Try again in five minutes.'),429
        user=db().execute('SELECT * FROM users WHERE email=? AND active=1',(str(data.get('email','')).lower(),)).fetchone()
        if not user or not check_password_hash(user['password'],str(data.get('password',''))):
            attempts[key]=recent+[now]
            return jsonify(error='Email or password is incorrect.'),401
        attempts.pop(key,None); session.clear(); session.update(uid=user['id'],csrf=secrets.token_hex(32)); session.permanent=True
        return jsonify(ok=True)

    @app.post('/api/logout')
    def logout():
        session.clear()
        return jsonify(ok=True)

    @app.get('/api/data')
    def all_data():
        conn=db(); contact=g.user['role']=='contact'
        where=' WHERE d.contact_id=?' if contact else ''
        params=(g.user['contact_id'],) if contact else ()
        documents=rows(conn,'SELECT d.*,c.name AS contact_name,o.notes FROM documents d JOIN contacts c ON c.id=d.contact_id JOIN orders o ON o.id=d.order_id'+where+' ORDER BY d.date DESC,d.id DESC',params)
        payments=rows(conn,'SELECT p.*,d.number AS document_number,d.kind,c.name AS contact_name FROM payments p JOIN documents d ON d.id=p.document_id JOIN contacts c ON c.id=d.contact_id'+where+' ORDER BY p.date DESC,p.id DESC',params)
        result=dict(documents=documents,payments=payments,workspace=workspace_data(conn),payment_requests=request_rows(conn,g.user['contact_id'] if contact else None),revision=conn.execute('SELECT revision FROM sync_state WHERE id=1').fetchone()[0],database=database_label(target))
        if not contact:
            for table in MASTER_FIELDS:
                result[table]=rows(conn,f'SELECT * FROM {table} ORDER BY id DESC')
            result['orders']=rows(conn,'SELECT o.*,c.name AS contact_name FROM orders o JOIN contacts c ON c.id=o.contact_id ORDER BY o.date DESC,o.id DESC')
            result['entries']=rows(conn,'SELECT e.*,j.name AS journal_name,SUM(l.debit) AS total FROM entries e JOIN journals j ON j.id=e.journal_id JOIN entry_lines l ON l.entry_id=e.id GROUP BY e.id,j.name ORDER BY e.date DESC,e.id DESC')
            result['expenses']=rows(conn,'SELECT x.*,a.name AS account_name FROM expenses x JOIN accounts a ON a.id=x.account_id ORDER BY x.date DESC,x.id DESC')
            result['stock']=rows(conn,"SELECT p.id,p.name,p.category,p.sku,p.unit,p.reorder_level,p.cost,p.active,COALESCE(SUM(s.quantity),0) AS quantity FROM products p LEFT JOIN stock_moves s ON s.product_id=p.id WHERE p.type!='Service' GROUP BY p.id")
            result['audit']=rows(conn,'SELECT a.*,u.name AS user_name FROM audit a LEFT JOIN users u ON u.id=a.user_id ORDER BY a.id DESC LIMIT 100')
            if g.user['role']=='admin':
                result['users']=rows(conn,'SELECT id,name,email,role,contact_id,active FROM users ORDER BY id')
        return jsonify(result)

    @app.post('/api/masters/<table>')
    @roles('admin','accountant')
    def create_master(table):
        require(table in MASTER_FIELDS,'Unknown master data type.')
        data=request.get_json(); conn=db()
        with conn:
            values=validate_master(conn,table,data)
            identifier=insert(conn,table,values)
            if table=='contacts' and data.get('portal_password'):
                password=text_value(data,'portal_password',True,200)
                require(len(password)>=10 and values['email'],'A portal account requires an email and a password of at least 10 characters.')
                insert(conn,'users',dict(name=values['name'],email=values['email'].lower(),password=generate_password_hash(password),role='contact',contact_id=identifier))
            audit(conn,g.user['id'],'Created',table,identifier,values['name'])
        return jsonify(id=identifier),201

    @app.patch('/api/masters/<table>/<int:identifier>')
    @roles('admin')
    def edit_master(table,identifier):
        require(table in MASTER_FIELDS,'Unknown master data type.')
        conn=db(); data=request.get_json()
        with conn:
            existing=record(conn,table,identifier)
            if 'active' in data:
                require(isinstance(data['active'],bool),'Active must be true or false.')
                if not data['active'] and table=='accounts':
                    require(not existing['system_key'],'System accounts cannot be archived.')
                    require(not conn.execute('SELECT 1 FROM journals WHERE active=1 AND (debit_account_id=? OR credit_account_id=?)',(identifier,identifier)).fetchone(),'Account is used by an active journal.')
                values={'active':int(data['active'])}
            else:
                values=validate_master(conn,table,data)
                if table in ('accounts','journals','products','contacts','analytics'):
                    # Preserve classification of already-linked records and all system accounts.
                    linked={'accounts':('entry_lines','account_id'),'journals':('entries','journal_id'),'products':('order_lines','product_id'),'contacts':('orders','contact_id'),'analytics':('entry_lines','analytic_id')}[table]
                    used=conn.execute(f'SELECT 1 FROM {linked[0]} WHERE {linked[1]}=? LIMIT 1',(identifier,)).fetchone()
                    if table=='accounts':
                        used=used or conn.execute('SELECT 1 FROM journals WHERE debit_account_id=? OR credit_account_id=?',(identifier,identifier)).fetchone()
                    if table=='analytics':
                        used=used or conn.execute('SELECT 1 FROM orders WHERE analytic_id=?',(identifier,)).fetchone() or conn.execute('SELECT 1 FROM budgets WHERE analytic_id=?',(identifier,)).fetchone()
                    require(values.get('type')==existing.get('type') or (not used and not existing.get('system_key')), 'The type of a used or system record cannot be changed.')
                if table=='journals':
                    require(not conn.execute('SELECT 1 FROM orders WHERE journal_id=?',(identifier,)).fetchone() or all(values[k]==existing[k] for k in ('type','debit_account_id','credit_account_id')), 'Journal defaults are locked after orders use them. Create another journal.')
            conn.execute(f'UPDATE {table} SET '+','.join(f'{k}=?' for k in values)+' WHERE id=?',(*values.values(),identifier))
            if table=='contacts' and 'active' in values:
                conn.execute('UPDATE users SET active=? WHERE contact_id=?',(values['active'],identifier))
            audit(conn,g.user['id'],'Updated',table,identifier,json.dumps({k:v for k,v in values.items() if k!='image'}))
        return jsonify(ok=True)

    @app.post('/api/users')
    @roles('admin')
    def create_user():
        data=request.get_json(); role=data.get('role'); require(role in ('admin','accountant','contact'),'Invalid role.')
        password=text_value(data,'password',True,200); require(len(password)>=10,'Use at least 10 characters for the password.')
        email=text_value(data,'email').lower(); require('@' in email,'Enter a valid email.')
        contact_id=record(db(),'contacts',data.get('contact_id'),True)['id'] if role=='contact' else None
        with db():
            uid=insert(db(),'users',dict(name=text_value(data,'name'),email=email,password=generate_password_hash(password),role=role,contact_id=contact_id))
            audit(db(),g.user['id'],'User created','users',uid,role)
        return jsonify(id=uid),201

    @app.patch('/api/users/<int:identifier>')
    @roles('admin')
    def update_user(identifier):
        data=request.get_json(); require(identifier!=g.user['id'],'You cannot disable your own account here.')
        record(db(),'users',identifier)
        with db():
            if 'password' in data:
                password=text_value(data,'password',True,200); require(len(password)>=10,'Use at least 10 characters.')
                db().execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),identifier))
            else:
                require(isinstance(data.get('active'),bool),'Choose an account status.')
                db().execute('UPDATE users SET active=? WHERE id=?',(int(data['active']),identifier))
            audit(db(),g.user['id'],'User updated','users',identifier)
        return jsonify(ok=True)

    @app.post('/api/password')
    def change_password():
        data=request.get_json(); current=db().execute('SELECT password FROM users WHERE id=?',(g.user['id'],)).fetchone()[0]
        require(check_password_hash(current,str(data.get('current',''))),'Current password is incorrect.')
        password=text_value(data,'password',True,200); require(len(password)>=10,'Use at least 10 characters.')
        with db():
            db().execute('UPDATE users SET password=? WHERE id=?',(generate_password_hash(password),g.user['id']))
        return jsonify(ok=True)

    @app.post('/api/orders')
    @roles('admin','accountant')
    def order_create():
        with db():
            identifier=create_order(db(),request.get_json(),g.user['id'])
        return jsonify(id=identifier),201

    @app.post('/api/orders/<int:identifier>/post')
    @roles('admin','accountant')
    def order_post(identifier):
        with db():
            db().execute('BEGIN IMMEDIATE')
            doc_id=post_order(db(),identifier,request.get_json(),g.user['id'])
        return jsonify(id=doc_id),201

    @app.post('/api/orders/<int:identifier>/cancel')
    @roles('admin','accountant')
    def cancel_order(identifier):
        with db():
            db().execute('BEGIN IMMEDIATE')
            order=record(db(),'orders',identifier); require(order['status']=='draft','Only draft orders can be cancelled.')
            db().execute("UPDATE orders SET status='cancelled' WHERE id=?",(identifier,))
            audit(db(),g.user['id'],'Cancelled','orders',identifier)
        return jsonify(ok=True)

    @app.get('/api/orders/<int:identifier>')
    @roles('admin','accountant')
    def order_detail(identifier):
        order=record(db(),'orders',identifier)
        return jsonify(order=order,lines=rows(db(),'SELECT * FROM order_lines WHERE order_id=?',(identifier,)))

    @app.get('/api/documents/<int:identifier>')
    def document_detail(identifier):
        doc=record(db(),'documents',identifier)
        if g.user['role']=='contact' and doc['contact_id']!=g.user['contact_id']:
            return jsonify(error='Access denied.'),403
        buyer=json.loads(doc.get('buyer_snapshot') or '{}') or record(db(),'contacts',doc['contact_id'])
        seller=json.loads(doc.get('seller_snapshot') or '{}') or workspace_data(db())
        return jsonify(document=doc,order=record(db(),'orders',doc['order_id']),contact=buyer,seller=seller,lines=rows(db(),'SELECT * FROM order_lines WHERE order_id=?',(doc['order_id'],)),payments=rows(db(),'SELECT * FROM payments WHERE document_id=? ORDER BY date,id',(identifier,)))

    @app.post('/api/documents/<int:identifier>/payments')
    @roles('admin','accountant')
    def payment_create(identifier):
        with db():
            db().execute('BEGIN IMMEDIATE')
            payment_id=register_payment(db(),identifier,request.get_json(),g.user)
        return jsonify(id=payment_id),201

    @app.post('/api/entries')
    @roles('admin','accountant')
    def entry_create():
        data=request.get_json(); conn=db()
        journal=record(conn,'journals',data.get('journal_id'),True); when=valid_date(data.get('date')); reference=text_value(data,'reference')
        items=data.get('lines',[]); require(isinstance(items,list) and 2<=len(items)<=100,'Add 2 to 100 journal lines.')
        posting=[]
        for item in items:
            require(isinstance(item, dict), 'Each journal line must be an object.')
            account=record(conn,'accounts',item.get('account_id'),True)
            require(account['system_key'] not in ('receivable','payable'), 'Use invoice and bill payments for receivable/payable control accounts.')
            debit=money(item.get('debit',0)); credit=money(item.get('credit',0)); require((debit>0) != (credit>0),'Each line needs either a debit or a credit.')
            analytic_id=item.get('analytic_id') or None
            if analytic_id:
                analytic=record(conn,'analytics',analytic_id,True)
                require(account['type']==analytic['type'],'Analytic type must match the income or expense account.')
            posting.append(line(account['id'],debit,credit,analytic=analytic_id))
        with conn:
            identifier=add_entry(conn,g.user['id'],journal['id'],when,reference,'manual',None,posting)
            audit(conn,g.user['id'],'Journal posted','entries',identifier,reference)
        return jsonify(id=identifier),201

    @app.get('/api/entries/<int:identifier>')
    @roles('admin','accountant')
    def entry_detail(identifier):
        return jsonify(entry=record(db(),'entries',identifier),lines=rows(db(),'SELECT l.*,a.name AS account_name,a.code FROM entry_lines l JOIN accounts a ON a.id=l.account_id WHERE entry_id=?',(identifier,)))

    def report_data():
        start=valid_date(request.args.get('start',date.today().replace(day=1).isoformat())); end=valid_date(request.args.get('end',date.today().isoformat())); require(start<=end,'Start date must not follow end date.')
        conn=db()
        balances=rows(conn,"SELECT a.*,COALESCE(SUM(CASE WHEN e.date<=? THEN l.debit-l.credit ELSE 0 END),0) AS balance,COALESCE(SUM(CASE WHEN e.date BETWEEN ? AND ? THEN l.debit-l.credit ELSE 0 END),0) AS period_balance FROM accounts a LEFT JOIN entry_lines l ON l.account_id=a.id LEFT JOIN entries e ON e.id=l.entry_id GROUP BY a.id ORDER BY a.code",(end,start,end))
        income=-sum(a['period_balance'] for a in balances if a['type']=='Income'); expenses=sum(a['period_balance'] for a in balances if a['type']=='Expense')
        assets=sum(a['balance'] for a in balances if a['type']=='Asset'); liabilities=-sum(a['balance'] for a in balances if a['type']=='Liability'); capital=-sum(a['balance'] for a in balances if a['type']=='Capital'); earnings=-sum(a['balance'] for a in balances if a['type'] in ('Income','Expense'))
        budgets=rows(conn,'SELECT b.*,a.name AS analytic_name,a.type AS analytic_type FROM budgets b JOIN analytics a ON a.id=b.analytic_id WHERE b.start_date<=? AND b.end_date>=? ORDER BY b.name',(end,start))
        for budget in budgets:
            low=max(start,budget['start_date']); high=min(end,budget['end_date'])
            budget['actual']=conn.execute('SELECT COALESCE(SUM(l.debit-l.credit),0) FROM entry_lines l JOIN entries e ON e.id=l.entry_id WHERE l.analytic_id=? AND e.date BETWEEN ? AND ?',(budget['analytic_id'],low,high)).fetchone()[0]*(-1 if budget['analytic_type']=='Income' else 1)
            budget['variance']=budget['actual']-budget['planned']
        stock=rows(conn,"SELECT p.id,p.name,p.category,p.cost,COALESCE(SUM(CASE WHEN s.date<=? THEN s.quantity ELSE 0 END),0) AS quantity FROM products p LEFT JOIN stock_moves s ON s.product_id=p.id WHERE p.type!='Service' GROUP BY p.id ORDER BY p.name",(end,))
        ledger=rows(conn,'SELECT e.date,e.number,e.reference,a.code,a.name AS account,l.debit,l.credit FROM entry_lines l JOIN entries e ON e.id=l.entry_id JOIN accounts a ON a.id=l.account_id WHERE e.date BETWEEN ? AND ? ORDER BY e.date,e.id,l.id',(start,end))
        return dict(start=start,end=end,accounts=balances,income=income,expenses=expenses,profit=income-expenses,assets=assets,liabilities=liabilities,capital=capital,earnings=earnings,balance_difference=assets-liabilities-capital-earnings,budgets=budgets,stock=stock,ledger=ledger)

    @app.get('/api/reports')
    @roles('admin','accountant')
    def reports():
        return jsonify(report_data())

    @app.get('/api/reports/export')
    @roles('admin','accountant')
    def export():
        report=report_data(); kind=request.args.get('kind','ledger')
        require(kind in ('ledger','stock','budgets','accounts'),'Unknown report.')
        output=io.StringIO(); writer=csv.writer(output)
        records=report[kind]
        money_fields={'debit','credit','balance','period_balance','planned','actual','variance','cost'}
        if records:
            fields=[k for k in records[0] if k not in ('system_key','active')]; writer.writerow(fields)
            for row in records:
                values=[]
                for key in fields:
                    val=row[key]
                    if key in money_fields: val=f'{val/100:.2f}'
                    if isinstance(val,str) and val.startswith(('=','+','-','@','\t','\r')): val="'"+val
                    values.append(val)
                writer.writerow(values)
        return app.response_class('\ufeff'+output.getvalue(),mimetype='text/csv',headers={'Content-Disposition':f'attachment; filename=urban-{kind}-{report["end"]}.csv'})

    @app.get('/api/backup')
    @roles('admin')
    def backup():
        if is_postgres(target):
            tables=list(MASTER_FIELDS)+['users','orders','order_lines','documents','entries','entry_lines','payments','stock_moves','audit','expenses','payment_requests','workspace']
            payload={table:rows(db(),f'SELECT * FROM {table}') for table in tables}
            return app.response_class(json.dumps(payload,default=str),mimetype='application/json',headers={'Content-Disposition':f'attachment; filename=urban-export-{date.today()}.json'})
        memory=sqlite3.connect(':memory:'); db().backup(memory); content=memory.serialize(); memory.close()
        return app.response_class(content,mimetype='application/vnd.sqlite3',headers={'Content-Disposition':f'attachment; filename=urban-backup-{date.today()}.sqlite3'})

    register_features(app,db,roles)
    return app


if __name__=='__main__':
    create_app().run(host=os.environ.get('URBAN_HOST','127.0.0.1'),port=int(os.environ.get('PORT','5050')),debug=False)
