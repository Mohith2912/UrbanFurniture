import unittest
from datetime import date, timedelta
import test_accounting


class LiveTests(unittest.TestCase):
    setUp=test_accounting.AccountingTests.setUp
    tearDown=test_accounting.AccountingTests.tearDown
    send=test_accounting.AccountingTests.send
    master=test_accounting.AccountingTests.master
    order=test_accounting.AccountingTests.order
    post=test_accounting.AccountingTests.post
    report=test_accounting.AccountingTests.report
    data=test_accounting.AccountingTests.data
    login_client=test_accounting.AccountingTests.login_client

    def test_setup_never_loads_sample_data(self):
        self.assertEqual(len(self.data()['contacts']),2)
        self.assertEqual(len(self.data()['products']),1)
        self.assertEqual(self.data()['documents'],[])

    def test_revision_advances_after_committed_write(self):
        before=self.client.get('/api/sync').json['revision']
        self.master('contacts',name='Actual Customer',type='Customer')
        after=self.client.get('/api/sync').json['revision']
        self.assertGreater(after,before)

    def test_failed_write_does_not_publish_revision(self):
        oid=self.order('sale',2)
        before=self.client.get('/api/sync').json['revision']
        self.post(oid,400)
        self.assertEqual(self.client.get('/api/sync').json['revision'],before)

    def test_event_stream_is_authenticated_and_contains_only_revision(self):
        self.assertEqual(self.app.test_client().get('/api/events').status_code,401)
        response=self.client.get('/api/events',buffered=False)
        first=next(response.response).decode()
        self.assertIn('event: change',first)
        self.assertIn('revision',first)
        self.assertNotIn('contact',first)
        response.close()

    def test_intra_state_gst_is_calculated_and_posted_separately(self):
        oid=self.order(qty=10,tax=18)
        doc=self.post(oid)['id'];detail=self.client.get(f'/api/documents/{doc}').json
        self.assertEqual(detail['order']['cgst'],5400)
        self.assertEqual(detail['order']['sgst'],5400)
        self.assertEqual(detail['order']['igst'],0)
        self.assertEqual(detail['document']['total'],70800)
        self.assertEqual(detail['lines'][0]['cgst']+detail['lines'][0]['sgst'],detail['lines'][0]['tax'])
        self.assertEqual(self.report()['balance_difference'],0)

    def test_inter_state_igst_and_exempt(self):
        oid=self.order(qty=2,tax=18,tax_mode='inter',place_of_supply='Maharashtra');self.post(oid)
        result=self.client.get(f'/api/orders/{oid}').json['order']
        self.assertEqual((result['cgst'],result['sgst'],result['igst']),(0,0,2160))
        oid=self.order(qty=2,tax=18,tax_mode='exempt');self.post(oid)
        result=self.client.get(f'/api/orders/{oid}').json['order']
        self.assertEqual((result['tax'],result['total']),(0,12000))

    def test_odd_paise_split_reconciles_exactly(self):
        oid=self.send('/orders',dict(kind='purchase',contact_id=self.vendor,journal_id=2,date='2026-09-01',due_date='2026-10-01',tax_mode='intra',lines=[dict(product_id=self.product,quantity=1,unit_price='.05',tax_rate=10)]),201)['id']
        self.post(oid)
        result=self.client.get(f'/api/orders/{oid}').json['lines'][0]
        self.assertEqual(result['tax'],1)
        self.assertEqual(result['cgst']+result['sgst'],1)

    def test_posted_invoice_identity_is_immutable(self):
        self.send('/workspace',dict(company_name='Real Company',address='Registered address',tax_id='24ABCDE1234F1Z5',state='Gujarat'),method='PATCH')
        oid=self.order();doc=self.post(oid)['id']
        self.send('/workspace',dict(company_name='Changed Company'),method='PATCH')
        self.send(f'/masters/contacts/{self.vendor}',dict(name='Changed Vendor',type='Vendor'),method='PATCH')
        invoice=self.client.get(f'/api/documents/{doc}').json
        self.assertEqual(invoice['seller']['company_name'],'Real Company')
        self.assertEqual(invoice['contact']['name'],'Azure Furniture')

    def test_product_hsn_and_unit_are_snapshotted(self):
        product=self.data()['products'][0]
        self.send(f'/masters/products/{self.product}',dict(name=product['name'],type='Goods',sales_price=100,cost=60,hsn='9403',unit='Nos',sku='CHAIR-001',reorder_level=3),method='PATCH')
        oid=self.order();result=self.client.get(f'/api/orders/{oid}').json['lines'][0]
        self.assertEqual((result['hsn'],result['unit']),('9403','Nos'))

    def test_expense_posts_cash_and_budget(self):
        self.master('budgets',name='Office costs',start_date='2026-09-01',end_date='2026-09-30',responsible='Owner',analytic_id=self.expense,planned=1000)
        self.send('/expenses',dict(name='Transport',date='2026-09-03',amount=150,method='Bank',account_id=10,analytic_id=self.expense,reference='Receipt R1'),201)
        self.assertEqual(self.data()['expenses'][0]['amount'],15000)
        r=self.report();self.assertEqual(r['expenses'],15000)
        self.assertEqual(r['budgets'][0]['actual'],15000)
        self.assertEqual(r['balance_difference'],0)

    def test_expense_rejects_invalid_account_and_negative_value(self):
        data=dict(name='Invalid',date='2026-09-03',amount=150,method='Bank',account_id=2)
        self.send('/expenses',data,400)
        data.update(account_id=10,amount=-1);self.send('/expenses',data,400)

    def test_payment_request_is_pending_until_reviewed_and_cannot_be_double_approved(self):
        self.post(self.order());invoice=self.post(self.order('sale',2))['id']
        self.send('/users',dict(name='Customer',email='customer@example.test',password='test-password-123',role='contact',contact_id=self.customer),201)
        c,t=self.login_client('customer@example.test')
        rid=self.send('/payment-requests',dict(document_id=invoice,date='2026-09-02',method='Bank',amount=50,reference='TRANSFER-1'),201,client=c,csrf=t)['id']
        self.assertEqual(self.client.get(f'/api/documents/{invoice}').json['document']['paid'],0)
        self.send(f'/payment-requests/{rid}/review',dict(decision='approved',note='Verified with bank'))
        self.assertEqual(self.client.get(f'/api/documents/{invoice}').json['document']['paid'],5000)
        self.send(f'/payment-requests/{rid}/review',dict(decision='approved'),400)

    def test_csv_preview_is_readonly_and_commit_is_atomic(self):
        content='name,type,sales_price,cost,category,sku,reorder_level\nDesk,Goods,900,500,Office,D-01,3\nTable,Goods,1500,1000,Living,T-01,2'
        preview=self.send('/import/products',dict(csv=content))
        self.assertEqual(preview['count'],2)
        self.assertEqual(len(self.data()['products']),1)
        self.send('/import/products',dict(csv=content,commit=True),201)
        self.assertEqual(len(self.data()['products']),3)
        self.send('/import/products',dict(csv=content,commit=True),400)
        self.assertEqual(len(self.data()['products']),3)

    def test_csv_invalid_row_prevents_all_inserts(self):
        content='name,type,sales_price,cost\nValid desk,Goods,900,500\nBad desk,Goods,-1,100'
        preview=self.send('/import/products',dict(csv=content))
        self.assertFalse(preview['valid']);self.assertEqual(preview['errors'][0]['row'],3)
        self.send('/import/products',dict(csv=content,commit=True),400)
        self.assertEqual(len(self.data()['products']),1)

    def test_statement_reconciles_document_payments(self):
        self.post(self.order());inv=self.post(self.order('sale',3))['id']
        self.send(f'/documents/{inv}/payments',dict(date='2026-09-02',method='Bank',amount=100),201)
        result=self.client.get(f'/api/contacts/{self.customer}/statement?end=2026-09-30').json
        self.assertEqual(result['closing'],25400)
        self.assertEqual(len(result['movements']),2)

    def test_insights_have_zeroes_not_fabricated_data(self):
        data=self.client.get('/api/insights').json
        self.assertEqual(data['totals'],dict(sale=0,purchase=0))
        self.assertEqual(data['cash'],0);self.assertEqual(data['trend'],[])
        self.assertEqual(len(data['low_stock']),1)

    def test_reorder_and_aging_reflect_real_transactions(self):
        self.post(self.order(qty=10));self.post(self.order('sale',2))
        result=self.client.get('/api/insights').json
        self.assertEqual(result['low_stock'],[])
        self.assertEqual(result['totals']['sale'],23600)

    def test_company_settings_are_owner_only(self):
        self.send('/users',dict(name='Bookkeeper',email='bookkeeper@example.test',role='accountant',password='test-password-123'),201)
        c,t=self.login_client('bookkeeper@example.test')
        self.send('/workspace',dict(company_name='No'),403,'PATCH',c,t)


if __name__=='__main__':unittest.main()
