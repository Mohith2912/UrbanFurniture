"""Isolated browser QA fixture; never touches the live workspace database."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from app import create_app
from waitress import serve

target=Path(__file__).resolve().parents[1]/'tmp'/'ui-qa-v2'/'workspace.sqlite3'
application=create_app(target,testing=True)
c=application.test_client();session=c.get('/api/session').json
token=session['csrf']
def post(path,data):
    response=c.post('/api'+path,json=data,headers={'X-CSRF-Token':token})
    assert response.status_code<300,response.json
    return response.json
if session['needs_setup']:
    post('/setup',dict(name='QA Owner',email='qa@example.test',password='qa-local-test-123'))
    c.patch('/api/workspace',json=dict(company_name='QA Furniture Studio',address='21 Design Avenue, Ahmedabad 380001',state='Gujarat',state_code='24',tax_id='24ABCDE1234F1Z5',email='accounts@example.test',phone='0000000000',bank_name='QA Bank',account_number='TEST-ACCOUNT',ifsc='TEST0000001',invoice_note='Payment due within 30 days. This is an isolated test invoice.'),headers={'X-CSRF-Token':token})
    vendor=post('/masters/contacts',dict(name='QA Timber Works',type='Vendor',state='Gujarat'))['id']
    buyer=post('/masters/contacts',dict(name='QA Design Office',type='Customer',email='buyer@example.test',address='42 Workspace Street',city='Ahmedabad',state='Gujarat',pincode='380015',gstin='24ABCDE5678G1Z2'))['id']
    product=post('/masters/products',dict(name='QA Oak Lounge Chair',type='Goods',sales_price=5000,cost=2000,category='Seating',sku='QA-CHAIR-01',hsn='9403',unit='Nos',reorder_level=5))['id']
    for kind,contact,qty,price,journal in [('purchase',vendor,20,2000,2),('sale',buyer,2,5000,1)]:
        order=post('/orders',dict(kind=kind,contact_id=contact,journal_id=journal,date='2026-09-18',due_date='2026-10-18',tax_mode='intra',place_of_supply='Gujarat',lines=[dict(product_id=product,quantity=qty,unit_price=price,tax_rate=18)]))['id']
        post(f'/orders/{order}/post',{})
print('Isolated browser QA workspace: http://127.0.0.1:5053',flush=True)
serve(application,host='127.0.0.1',port=5053,threads=16)
