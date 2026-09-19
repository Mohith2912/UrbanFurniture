'use client';

import { useState } from 'react';
import { Plus, ShoppingCart, Trash2 } from 'lucide-react';
import { send } from '@/lib/api';
import { dateText, dueDate, money, today } from '@/lib/format';
import { Empty, FormMessage, Modal, PageIntro, Panel, Status } from '@/components/page-ui';
import { useWorkspace } from '@/components/workspace-provider';

const blankLine = () => ({ key: `${Date.now()}-${Math.random()}`, product_id: '', quantity: '1', unit_price: '', tax_rate: '18' });

export default function OrdersPage() {
  const { data, refresh } = useWorkspace();
  const [open, setOpen] = useState(false);
  const [kind, setKind] = useState('sale');
  const [lines, setLines] = useState([blankLine()]);
  const [error, setError] = useState('');
  const orders = data.orders || [];
  const products = (data.products || []).filter((p) => p.active !== 0);
  const contacts = (data.contacts || []).filter((c) => c.active !== 0 && (c.type === 'Both' || c.type === (kind === 'sale' ? 'Customer' : 'Vendor')));
  const journals = (data.journals || []).filter((j) => j.active !== 0 && j.type === (kind === 'sale' ? 'Sales' : 'Purchase'));
  function newOrder(nextKind) { setKind(nextKind); setLines([blankLine()]); setError(''); setOpen(true); }
  function chooseProduct(index, productId) { const product = products.find((p) => String(p.id) === productId); setLines((current) => current.map((line, i) => i === index ? { ...line, product_id: productId, unit_price: ((kind === 'sale' ? product?.sales_price : product?.cost) / 100 || 0).toFixed(2) } : line)); }
  async function create(event) {
    event.preventDefault(); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try { await send('/orders', 'POST', { ...values, kind, lines: lines.map(({ key, ...line }) => line) }); await refresh(); setOpen(false); }
    catch (err) { setError(err.message); }
  }
  async function post(order) { try { await send(`/orders/${order.id}/post`, 'POST', { date: order.date, due_date: order.due_date }); await refresh(); } catch (err) { setError(err.message); } }
  async function cancel(order) { try { await send(`/orders/${order.id}/cancel`, 'POST', {}); await refresh(); } catch (err) { setError(err.message); } }
  return <><PageIntro eyebrow="ORDER TO INVOICE" title="Sales and purchases" description="Create draft orders, calculate GST on the backend and post them into permanent invoices or vendor bills." action={<><button className="soft-link" onClick={() => newOrder('purchase')}><Plus size={15} /> Purchase order</button><button className="next-primary compact" onClick={() => newOrder('sale')}><Plus size={15} /> Sales order</button></>} />
    <FormMessage error={error} />
    <Panel eyebrow="ORDER REGISTER" title="Sales and purchase orders" meta={`${orders.length} records`}>{orders.length ? <div className="section-table">{orders.map((order) => <div className="section-row order-row" key={order.id}><span><b>{order.number}</b><small>{order.contact_name} · {dateText(order.date)}</small></span><span><strong>{money(order.total)}</strong><small>{order.kind === 'sale' ? 'Sales order' : 'Purchase order'}</small></span><Status tone={order.status === 'posted' ? 'green' : order.status === 'cancelled' ? 'red' : 'amber'}>{order.status}</Status>{order.status === 'draft' && <span className="row-actions"><button className="next-primary compact" onClick={() => post(order)}>Post</button><button className="soft-link" onClick={() => cancel(order)}>Cancel</button></span>}</div>)}</div> : <Empty icon={ShoppingCart} title="No orders yet" text="Create a purchase order to receive stock or a sales order to issue an invoice." />}</Panel>
    {open && <Modal title={`New ${kind === 'sale' ? 'sales' : 'purchase'} order`} onClose={() => setOpen(false)} wide><form className="next-form-grid" onSubmit={create}><label>{kind === 'sale' ? 'Customer' : 'Vendor'}<select name="contact_id" required><option value="">Select contact</option>{contacts.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></label><label>Journal<select name="journal_id" required><option value="">Select journal</option>{journals.map((j) => <option key={j.id} value={j.id}>{j.name}</option>)}</select></label><label>Order date<input name="date" type="date" defaultValue={today()} required /></label><label>Due date<input name="due_date" type="date" defaultValue={dueDate(data.workspace?.default_terms)} required /></label><label>GST treatment<select name="tax_mode" defaultValue="intra"><option value="intra">CGST and SGST</option><option value="inter">IGST</option><option value="exempt">Tax exempt</option></select></label><label>Place of supply<input name="place_of_supply" defaultValue={data.workspace?.state || ''} /></label><div className="order-editor full"><div className="order-editor-head"><strong>Order items</strong><button type="button" className="soft-link" onClick={() => setLines((v) => [...v, blankLine()])}><Plus size={14} /> Add line</button></div>{lines.map((line, index) => <div className="order-edit-line" key={line.key}><label>Product<select value={line.product_id} onChange={(e) => chooseProduct(index, e.target.value)} required><option value="">Select product</option>{products.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}</select></label><label>Quantity<input type="number" min="0.001" step="0.001" value={line.quantity} onChange={(e) => setLines((v) => v.map((x, i) => i === index ? { ...x, quantity: e.target.value } : x))} required /></label><label>Price<input type="number" min="0" step="0.01" value={line.unit_price} onChange={(e) => setLines((v) => v.map((x, i) => i === index ? { ...x, unit_price: e.target.value } : x))} required /></label><label>Tax %<input type="number" min="0" max="100" step="0.01" value={line.tax_rate} onChange={(e) => setLines((v) => v.map((x, i) => i === index ? { ...x, tax_rate: e.target.value } : x))} required /></label><button type="button" className="remove-line" onClick={() => lines.length > 1 && setLines((v) => v.filter((_, i) => i !== index))} aria-label="Remove line"><Trash2 size={16} /></button></div>)}</div><label className="full">Notes<textarea name="notes" rows={3} /></label><FormMessage error={error} /><div className="dialog-actions full"><button type="button" className="soft-link" onClick={() => setOpen(false)}>Cancel</button><button className="next-primary compact" type="submit">Create draft order</button></div></form></Modal>}
  </>;
}
