'use client';

import { useState } from 'react';
import { FileText, Search } from 'lucide-react';
import { api } from '@/lib/api';
import { dateText, money } from '@/lib/format';
import { Empty, Modal, PageIntro, Panel, Status } from '@/components/page-ui';
import InvoiceView from '@/components/invoice-view';
import { useWorkspace } from '@/components/workspace-provider';

export default function DocumentsPage() {
  const { data, refresh } = useWorkspace();
  const [query, setQuery] = useState('');
  const [detail, setDetail] = useState(null);
  const [error, setError] = useState('');
  const records = (data.documents || []).filter((item) => `${item.number} ${item.contact_name}`.toLowerCase().includes(query.toLowerCase()));
  async function open(id) { try { setDetail(await api(`/documents/${id}`)); setError(''); } catch (err) { setError(err.message); } }
  async function updated() { await refresh(); setDetail(await api(`/documents/${detail.document.id}`)); }
  return <><PageIntro eyebrow="SALES AND PURCHASE RECORDS" title="Invoices and bills" description="Open, print and settle every posted customer invoice and vendor bill." />
    <div className="section-toolbar"><label className="search-control"><Search size={15} /><input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search documents" /></label><span>{records.length} records</span></div>
    {error && <p className="form-message error">{error}</p>}
    <Panel eyebrow="POSTED DOCUMENTS" title="Document register" meta={`${records.length} records`}>{records.length ? <div className="section-table">{records.map((item) => { const balance = item.total - item.paid; return <button className="section-row row-button" key={item.id} onClick={() => open(item.id)}><span><b>{item.number}</b><small>{item.contact_name} · {dateText(item.date)}</small></span><span><strong>{money(item.total)}</strong><small>{balance > 0 ? `${money(balance)} due ${dateText(item.due_date)}` : 'Paid in full'}</small></span><Status tone={balance <= 0 ? 'green' : new Date(item.due_date) < new Date() ? 'red' : 'amber'}>{balance <= 0 ? 'Paid' : 'Open'}</Status></button>; })}</div> : <Empty icon={FileText} title="No invoices or bills" text="Post a sales or purchase order to create the first document." />}</Panel>
    {detail && <Modal title={detail.document.number} onClose={() => setDetail(null)} wide><InvoiceView detail={detail} onUpdated={updated} /></Modal>}
  </>;
}
