import csv
import io
import sqlite3
import tempfile
import unittest
import os
import uuid
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode,quote
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from app import create_app


class AccountingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.database = Path(self.temp.name) / 'test.sqlite3'
        self.pg_schema=None
        if os.environ.get('URBAN_TEST_POSTGRES'):
            import psycopg
            from psycopg import sql
            self.pg_schema='urban_test_'+uuid.uuid4().hex
            with psycopg.connect(os.environ['URBAN_TEST_POSTGRES'],autocommit=True) as pg:
                pg.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.pg_schema)))
            parts=urlsplit(os.environ['URBAN_TEST_POSTGRES'])
            query=urlencode(parse_qsl(parts.query)+[('options','-c search_path='+self.pg_schema)],quote_via=quote)
            self.database=urlunsplit((parts.scheme,parts.netloc,parts.path,query,parts.fragment))
        self.app = create_app(self.database, testing=True)
        self.client = self.app.test_client()
        self.csrf = self.client.get('/api/session').json['csrf']
        self.send('/setup', dict(name='Owner', email='owner@example.test', password='test-password-123'))
        self.vendor = self.master('contacts', name='Azure Furniture', type='Vendor')
        self.customer = self.master('contacts', name='Nimesh Pathak', type='Customer', email='nimesh@example.test')
        self.product = self.master('products', name='Office Chair', type='Goods', sales_price=100, cost=60, category='Seating')
        self.income = self.master('analytics', name='Showroom income', type='Income')
        self.expense = self.master('analytics', name='Showroom purchases', type='Expense')

    def tearDown(self):
        if self.pg_schema:
            import psycopg
            from psycopg import sql
            assert self.pg_schema.startswith('urban_test_') and len(self.pg_schema)==43
            with psycopg.connect(os.environ['URBAN_TEST_POSTGRES'],autocommit=True) as pg:
                pg.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.pg_schema)))
        self.temp.cleanup()

    def send(self, path, data, status=200, method='POST', client=None, csrf=None):
        result = (client or self.client).open('/api'+path, method=method, json=data, headers={'X-CSRF-Token': csrf or self.csrf})
        self.assertEqual(result.status_code, status, result.get_json())
        return result.get_json()

    def master(self, table, **data):
        return self.send('/masters/'+table, data, 201)['id']

    def order(self, kind='purchase', qty=10, when='2026-09-01', tax=18, **extra):
        return self.send('/orders', dict(kind=kind, contact_id=self.vendor if kind=='purchase' else self.customer, journal_id=2 if kind=='purchase' else 1, date=when, due_date='2026-10-01', analytic_id=self.expense if kind=='purchase' else self.income, lines=[dict(product_id=self.product, quantity=qty, unit_price=60 if kind=='purchase' else 100, tax_rate=tax)], **extra), 201)['id']

    def post(self, oid, status=201, **data):
        return self.send(f'/orders/{oid}/post', data, status)

    def report(self, start='2026-09-01', end='2026-09-30'):
        response = self.client.get(f'/api/reports?start={start}&end={end}')
        self.assertEqual(response.status_code, 200)
        return response.json

    def data(self):
        return self.client.get('/api/data').json

    def login_client(self, email, password='test-password-123'):
        client = self.app.test_client()
        csrf = client.get('/api/session').json['csrf']
        self.send('/login', dict(email=email,password=password), client=client, csrf=csrf)
        return client, client.get('/api/session').json['csrf']

    def test_complete_purchase_sale_partial_and_full_payment(self):
        bill = self.post(self.order())['id']
        self.send(f'/documents/{bill}/payments',dict(date='2026-09-02',method='Bank',amount='708',reference='Purchase paid'),201)
        invoice = self.post(self.order('sale',5,when='2026-09-03'))['id']
        self.send(f'/documents/{invoice}/payments',dict(date='2026-09-03',method='Cash',amount='200',reference='Deposit'),201)
        detail = self.client.get(f'/api/documents/{invoice}').json
        self.assertEqual(detail['document']['total'],59000)
        self.assertEqual(detail['document']['paid'],20000)
        self.send(f'/documents/{invoice}/payments',dict(date='2026-09-04',method='Bank',amount='390'),201)
        r=self.report()
        self.assertEqual((r['income'],r['expenses'],r['profit']),(50000,60000,-10000))
        self.assertEqual(r['balance_difference'],0)
        self.assertEqual(r['stock'][0]['quantity'],5)
        self.assertEqual(sum(l['debit'] for l in r['ledger']),sum(l['credit'] for l in r['ledger']))
        balances={a['system_key']:a['balance'] for a in r['accounts']}
        self.assertEqual(balances['receivable'],0)
        self.assertEqual(balances['payable'],0)
        self.assertEqual(balances['cgst_input'],5400)
        self.assertEqual(balances['sgst_input'],5400)
        self.assertEqual(balances['cgst_output'],-4500)
        self.assertEqual(balances['sgst_output'],-4500)

    def test_draft_orders_do_not_post_stock_or_ledger(self):
        self.order()
        self.assertEqual(self.data()['entries'],[])
        self.assertEqual(self.report()['stock'][0]['quantity'],0)

    def test_conversion_is_one_time_and_atomic(self):
        oid=self.order(); self.post(oid); self.post(oid,400)
        self.assertEqual(len(self.data()['documents']),1)
        self.assertEqual(self.report()['stock'][0]['quantity'],10)

    def test_insufficient_stock_rolls_back_everything(self):
        oid=self.order('sale',1); self.post(oid,400)
        data=self.data()
        self.assertEqual(data['documents'],[])
        self.assertEqual(data['entries'],[])
        self.assertEqual(data['orders'][0]['status'],'draft')

    def test_duplicate_product_lines_are_aggregated_for_stock(self):
        self.post(self.order(qty=10))
        payload=dict(kind='sale',contact_id=self.customer,journal_id=1,date='2026-09-02',due_date='2026-10-01',lines=[dict(product_id=self.product,quantity=6,unit_price=100)]*2)
        oid=self.send('/orders',payload,201)['id']; self.post(oid,400)
        self.assertEqual(self.report()['stock'][0]['quantity'],10)

    def test_backdated_sale_cannot_break_future_stock(self):
        self.post(self.order(qty=10))
        self.post(self.order('sale',10,when='2026-09-10'))
        self.post(self.order(qty=10,when='2026-09-20'))
        oid=self.order('sale',1,when='2026-09-05'); self.post(oid,400)
        self.assertEqual(self.report()['stock'][0]['quantity'],10)

    def test_services_do_not_require_or_move_stock(self):
        service=self.master('products',name='Assembly',type='Service',sales_price=500,cost=0)
        oid=self.send('/orders',dict(kind='sale',contact_id=self.customer,journal_id=1,date='2026-09-01',due_date='2026-10-01',lines=[dict(product_id=service,quantity=2,unit_price=500,tax_rate=0)]),201)['id']
        self.post(oid)
        self.assertEqual(self.report()['income'],100000)
        self.assertEqual(len(self.report()['stock']),1)

    def test_combo_tracks_as_whole_stock_item(self):
        self.product=self.master('products',name='Dining set',type='Combo',sales_price=100,cost=60)
        self.post(self.order(qty=3));self.post(self.order('sale',qty=1))
        self.assertEqual(next(s for s in self.report()['stock'] if s['id']==self.product)['quantity'],2)

    def test_rounding_uses_half_up_at_line_level(self):
        oid=self.send('/orders',dict(kind='purchase',contact_id=self.vendor,journal_id=2,date='2026-09-01',due_date='2026-10-01',lines=[dict(product_id=self.product,quantity='1',unit_price='0.05',tax_rate='10'),dict(product_id=self.product,quantity='1.5',unit_price='0.01',tax_rate='0')]),201)['id']
        order=self.client.get(f'/api/orders/{oid}').json
        self.assertEqual(order['order']['subtotal'],7)
        self.assertEqual(order['order']['tax'],1)
        self.assertEqual(order['order']['total'],8)

    def test_overpayment_and_bad_dates_are_rejected(self):
        bill=self.post(self.order())['id']
        self.send(f'/documents/{bill}/payments',dict(date='2026-09-02',method='Bank',amount='708.01'),400)
        self.send(f'/documents/{bill}/payments',dict(date='2026-08-31',method='Bank',amount='1'),400)
        self.send(f'/documents/{bill}/payments',dict(date='2026-09-02',method='Card',amount='1'),400)
        self.assertEqual(self.data()['payments'],[])

    def test_zero_negative_nan_and_infinite_amounts_are_rejected(self):
        bill=self.post(self.order())['id']
        for amount in ['0','-1','NaN','Infinity','1e1000','hello']:
            self.send(f'/documents/{bill}/payments',dict(date='2026-09-02',method='Bank',amount=amount),400)

    def test_concurrent_payment_cannot_overpay(self):
        bill=self.post(self.order(qty=1,tax=0))['id']
        def pay(_):
            client,csrf=self.login_client('owner@example.test')
            return client.post(f'/api/documents/{bill}/payments',json=dict(date='2026-09-02',method='Bank',amount=60),headers={'X-CSRF-Token':csrf}).status_code
        with ThreadPoolExecutor(max_workers=2) as pool:
            codes=list(pool.map(pay,range(2)))
        self.assertEqual(sorted(codes),[201,400])
        self.assertEqual(len(self.data()['payments']),1)

    def test_period_reports_use_historical_dates(self):
        self.post(self.order(qty=10))
        inv=self.post(self.order('sale',qty=5,when='2026-09-10'))['id']
        self.send(f'/documents/{inv}/payments',dict(date='2026-10-01',method='Cash',amount=590),201)
        r=self.report(end='2026-09-09')
        self.assertEqual(r['income'],0)
        self.assertEqual(r['stock'][0]['quantity'],10)
        r=self.report(end='2026-09-30')
        self.assertEqual(next(a for a in r['accounts'] if a['system_key']=='receivable')['balance'],59000)
        self.assertEqual(self.report(start='2026-10-01',end='2026-10-31')['income'],0)

    def test_budget_actuals_link_analytics_and_period(self):
        self.master('budgets',name='Revenue target',start_date='2026-09-01',end_date='2026-09-30',responsible='Owner',analytic_id=self.income,planned=1000)
        self.post(self.order());self.post(self.order('sale',qty=5))
        budget=self.report()['budgets'][0]
        self.assertEqual((budget['planned'],budget['actual'],budget['variance']),(100000,50000,-50000))
        self.assertEqual(self.report(start='2026-10-01',end='2026-10-31')['budgets'],[])

    def test_manual_journal_must_balance_and_control_accounts_are_protected(self):
        payload=dict(journal_id=5,date='2026-09-01',reference='Owner investment',lines=[dict(account_id=2,debit=1000,credit=0),dict(account_id=7,debit=0,credit=900)])
        self.send('/entries',payload,400)
        payload['lines'][1]['credit']=1000
        self.send('/entries',payload,201)
        self.assertEqual(self.report()['balance_difference'],0)
        payload['lines'][0]['account_id']=3
        self.send('/entries',payload,400)

    def test_operating_expense_flows_to_budget(self):
        self.master('budgets',name='Costs',start_date='2026-09-01',end_date='2026-09-30',responsible='Owner',analytic_id=self.expense,planned=500)
        self.send('/entries',dict(journal_id=5,date='2026-09-01',reference='Showroom supplies',lines=[dict(account_id=10,debit=150,credit=0,analytic_id=self.expense),dict(account_id=2,debit=0,credit=150)]),201)
        self.assertEqual(self.report()['budgets'][0]['actual'],15000)

    def test_accountant_can_create_but_not_edit_archive_or_manage_users(self):
        self.send('/users',dict(name='Accountant',email='accountant@example.test',password='test-password-123',role='accountant'),201)
        c,t=self.login_client('accountant@example.test')
        self.send('/masters/contacts',dict(name='New client',type='Customer'),201,client=c,csrf=t)
        self.send(f'/masters/contacts/{self.customer}',dict(active=False),403,'PATCH',c,t)
        self.send('/users',dict(name='X'),403,client=c,csrf=t)
        self.assertEqual(c.get('/api/reports').status_code,200)
        self.assertEqual(c.get('/api/backup').status_code,403)
        self.assertNotIn('users',c.get('/api/data').json)

    def test_contact_isolation_and_payment_scope(self):
        self.post(self.order());invoice=self.post(self.order('sale',qty=2))['id']
        other=self.master('contacts',name='Other customer',type='Customer')
        old=self.customer;self.customer=other;foreign=self.post(self.order('sale',qty=1))['id'];self.customer=old
        self.send('/users',dict(name='Nimesh',email='portal@example.test',password='test-password-123',role='contact',contact_id=self.customer),201)
        c,t=self.login_client('portal@example.test')
        result=c.get('/api/data').json
        self.assertEqual(set(result),{'documents','payments','payment_requests','workspace','revision','database'})
        self.assertEqual([d['id'] for d in result['documents']],[invoice])
        self.assertEqual(c.get(f'/api/documents/{foreign}').status_code,403)
        self.assertEqual(c.get('/api/reports').status_code,403)
        self.send(f'/documents/{foreign}/payments',dict(date='2026-09-02',method='Bank',amount=10),403,client=c,csrf=t)
        self.send(f'/documents/{invoice}/payments',dict(date='2026-09-02',method='Bank',amount=10),403,client=c,csrf=t)
        self.send('/payment-requests',dict(document_id=invoice,date='2026-09-02',method='Bank',amount=10,reference='Bank transfer'),201,client=c,csrf=t)
        self.send('/masters/products',dict(name='Invalid'),403,client=c,csrf=t)

    def test_contact_creation_can_provision_portal_and_archive_revokes_access(self):
        cid=self.master('contacts',name='Portal Person',type='Both',email='person@example.test',portal_password='test-password-123')
        c,t=self.login_client('person@example.test')
        self.assertEqual(c.get('/api/data').status_code,200)
        self.send(f'/masters/contacts/{cid}',dict(active=False),method='PATCH')
        self.assertEqual(c.get('/api/data').status_code,401)

    def test_master_archive_preserves_history_and_blocks_new_orders(self):
        self.post(self.order())
        self.send(f'/masters/products/{self.product}',dict(active=False),method='PATCH')
        self.assertEqual(len(self.data()['documents']),1)
        self.assertEqual(self.report()['stock'][0]['quantity'],10)
        self.send('/orders',dict(kind='purchase',contact_id=self.vendor,journal_id=2,date='2026-09-01',due_date='2026-10-01',lines=[dict(product_id=self.product,quantity=1,unit_price=60)]),400)
        self.send(f'/masters/products/{self.product}',dict(active=True),method='PATCH')
        self.order()

    def test_invalid_contact_journal_and_analytic_types_are_rejected(self):
        payload=dict(kind='sale',contact_id=self.vendor,journal_id=1,date='2026-09-01',due_date='2026-10-01',lines=[dict(product_id=self.product,quantity=1,unit_price=100)])
        self.send('/orders',payload,400);payload['contact_id']=self.customer;payload['journal_id']=2
        self.send('/orders',payload,400);payload['journal_id']=1;payload['analytic_id']=self.expense
        self.send('/orders',payload,400)

    def test_journal_defaults_and_account_types_preserve_posted_classification(self):
        self.post(self.order())
        self.send('/masters/journals/2',dict(name='Purchases',type='Purchase',debit_account_id=10,credit_account_id=5),400,'PATCH')
        self.send('/masters/accounts/9',dict(name='Purchases',code='5000',type='Income'),400,'PATCH')
        self.send('/masters/accounts/1',dict(active=False),400,'PATCH')

    def test_cancel_only_draft(self):
        oid=self.order();self.send(f'/orders/{oid}/cancel',{})
        self.post(oid,400)
        oid=self.order();self.post(oid)
        self.send(f'/orders/{oid}/cancel',{},400)

    def test_auth_csrf_and_bad_payload(self):
        self.assertEqual(self.app.test_client().get('/api/data').status_code,401)
        self.assertEqual(self.client.post('/api/orders',json={}).status_code,403)
        self.send('/setup',dict(name='Again',email='again@example.test',password='test-password-123'),400)
        self.send('/orders',[],400)
        self.send('/orders',dict(kind='purchase',contact_id=self.vendor,journal_id=2,date='2026-09-01',due_date='2026-10-01',lines=['bad']),400)

    def test_backup_is_valid_and_durable(self):
        self.post(self.order())
        response=self.client.get('/api/backup')
        self.assertEqual(response.status_code,200)
        if self.pg_schema:
            self.assertEqual(len(response.json['documents']),1)
            app2=create_app(self.database,testing=True)
            self.assertFalse(app2.test_client().get('/api/session').json['needs_setup'])
            return
        backup=Path(self.temp.name)/'backup.sqlite3';backup.write_bytes(response.data)
        with closing(sqlite3.connect(backup)) as conn:
            self.assertEqual(conn.execute('PRAGMA integrity_check').fetchone()[0],'ok')
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM documents').fetchone()[0],1)
        app2=create_app(self.database,testing=True)
        self.assertFalse(app2.test_client().get('/api/session').json['needs_setup'])

    def test_csv_export_has_rupees_and_escapes_formula(self):
        self.send('/entries',dict(journal_id=5,date='2026-09-01',reference='=SUM(A1)',lines=[dict(account_id=2,debit=100,credit=0),dict(account_id=7,debit=0,credit=100)]),201)
        response=self.client.get('/api/reports/export?start=2026-09-01&end=2026-09-30&kind=ledger')
        parsed=list(csv.DictReader(io.StringIO(response.data.decode('utf-8-sig'))))
        self.assertEqual(parsed[0]['debit'],'100.00')
        self.assertEqual(parsed[0]['reference'],"'=SUM(A1)")


if __name__ == '__main__':
    unittest.main()
