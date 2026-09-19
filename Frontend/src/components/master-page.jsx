'use client';

import { useState } from 'react';
import { Boxes, Plus, Search, Users } from 'lucide-react';
import { send } from '@/lib/api';
import { money } from '@/lib/format';
import { Empty, FormMessage, Modal, PageIntro, Panel, Status } from './page-ui';
import { useWorkspace } from './workspace-provider';

const definitions = {
  contacts: { eyebrow: 'CUSTOMERS AND VENDORS', title: 'Contacts', description: 'Keep customer, vendor, address and GST details ready for every transaction.', icon: Users },
  products: { eyebrow: 'CATALOGUE AND STOCK', title: 'Products and services', description: 'Maintain prices, purchase costs, GST classification and reorder information.', icon: Boxes },
};

export default function MasterPage({ type }) {
  const { data, refresh } = useWorkspace();
  const def = definitions[type];
  const records = data[type] || [];
  const [query, setQuery] = useState('');
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const filtered = records.filter((item) => `${item.name} ${item.email || ''} ${item.sku || ''} ${item.category || ''}`.toLowerCase().includes(query.toLowerCase()));
  async function submit(event) {
    event.preventDefault(); setError('');
    const form = Object.fromEntries(new FormData(event.currentTarget));
    try { await send(`/masters/${type}`, 'POST', form); await refresh(); setOpen(false); }
    catch (err) { setError(err.message); }
  }
  return <><PageIntro eyebrow={def.eyebrow} title={def.title} description={def.description} action={<button className="next-primary compact" onClick={() => setOpen(true)}><Plus size={15} /> Add {type === 'contacts' ? 'contact' : 'product'}</button>} />
    <div className="section-toolbar"><label className="search-control"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder={`Search ${type}`} /></label><span>{filtered.length} records</span></div>
    <Panel eyebrow="LIVE MASTER DATA" title={def.title} meta={`${records.filter((r) => r.active !== 0).length} active`}>{filtered.length ? <div className="data-grid">{filtered.map((item) => <article className="record-card" key={item.id}><div><strong>{item.name}</strong><small>{type === 'contacts' ? item.email || item.mobile || 'No contact details' : `${item.category || item.type} · ${item.sku || 'No SKU'}`}</small></div>{type === 'contacts' ? <><Status tone={item.type === 'Customer' ? 'green' : 'neutral'}>{item.type}</Status><p>{[item.city, item.state].filter(Boolean).join(', ') || 'Address not provided'}</p><small>{item.gstin ? `GSTIN ${item.gstin}` : 'GSTIN not provided'}</small></> : <><Status tone={item.type === 'Service' ? 'neutral' : 'green'}>{item.type}</Status><p>Sales {money(item.sales_price)} · Cost {money(item.cost)}</p><small>HSN/SAC {item.hsn || 'not set'} · {item.unit || 'Nos'}</small></>}</article>)}</div> : <Empty icon={def.icon} title={`No ${type} found`} text="Add the first record to start using this section." />}</Panel>
    {open && <Modal title={`Add ${type === 'contacts' ? 'contact' : 'product'}`} onClose={() => setOpen(false)}><form className="next-form-grid" onSubmit={submit}><label>Name<input name="name" required /></label>{type === 'contacts' ? <><label>Type<select name="type" defaultValue="Customer"><option>Customer</option><option>Vendor</option><option>Both</option></select></label><label>Email<input name="email" type="email" /></label><label>Mobile<input name="mobile" /></label><label>GSTIN<input name="gstin" maxLength={15} /></label><label>City<input name="city" /></label><label>State<input name="state" /></label><label>Pincode<input name="pincode" /></label><label className="full">Address<textarea name="address" rows={3} /></label></> : <><label>Type<select name="type" defaultValue="Goods"><option>Goods</option><option>Service</option><option>Combo</option></select></label><label>SKU<input name="sku" /></label><label>Category<input name="category" /></label><label>Sales price<input name="sales_price" type="number" min="0" step="0.01" required /></label><label>Purchase cost<input name="cost" type="number" min="0" step="0.01" required /></label><label>HSN or SAC<input name="hsn" /></label><label>Unit<input name="unit" defaultValue="Nos" /></label><label>Reorder level<input name="reorder_level" type="number" min="0" step="0.001" defaultValue="5" /></label></>}<FormMessage error={error} /><div className="dialog-actions full"><button type="button" className="soft-link" onClick={() => setOpen(false)}>Cancel</button><button className="next-primary compact" type="submit">Save record</button></div></form></Modal>}
  </>;
}
