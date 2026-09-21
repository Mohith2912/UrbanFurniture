'use client';

import Link from 'next/link';
import { Activity, ArrowUpRight, Database, FileText, IndianRupee, ReceiptText, WalletCards } from 'lucide-react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel } from '@/components/page-ui';
import { money } from '@/lib/format';

export default function DashboardPage() {
  const { user, data } = useWorkspace();
  const documents = data.documents || [];
  const outstanding = documents.reduce((sum, item) => sum + Number(item.total || 0) - Number(item.paid || 0), 0);
  const billed = documents.reduce((sum, item) => sum + Number(item.total || 0), 0);
  const collected = documents.reduce((sum, item) => sum + Number(item.paid || 0), 0);
  const collectionRate = billed ? Math.min(100, Math.round((collected / billed) * 100)) : 0;
  const roleCopy = user.role === 'admin' ? 'Manage the whole company, financial controls and access from one secure workspace.' : user.role === 'accountant' ? 'Keep sales, purchases, payments and reports moving from one accounting desk.' : 'Review your invoices, balances and payment history.';
  const metrics = [
    { label: 'Documents', value: documents.length, detail: 'Invoices and bills', icon: ReceiptText },
    { label: 'Outstanding', value: money(outstanding, 0), detail: 'Current receivable balance', icon: IndianRupee, featured: true },
    { label: 'Payments', value: data.payments?.length || 0, detail: 'Recorded settlements', icon: WalletCards },
    { label: 'Database', value: 'Live', detail: data.database, icon: Database },
  ];
  return <><PageIntro eyebrow={user.role === 'contact' ? 'PARTNER PORTAL' : 'BUSINESS CONTROL CENTRE'} title={`Welcome back, ${user.name?.split(' ')[0]}.`} description={roleCopy} action={<><Link className="next-primary compact" href="/documents">View invoices <ArrowUpRight size={15} /></Link>{user.role !== 'contact' && <Link className="soft-link" href="/orders">Create order</Link>}</>} />
    <section className="next-metrics dashboard-metrics">{metrics.map(({ label, value, detail, icon: Icon, featured }) => <article className={featured ? 'featured' : ''} key={label}><div className="metric-head"><span>{label}</span><i><Icon size={16} /></i></div><strong>{value}</strong><small>{detail}</small></article>)}</section>
    <section className="next-grid dashboard-grid"><Panel eyebrow="RECENT RECORDS" title="Invoices and bills" meta={<Link className="panel-link" href="/documents">View all <ArrowUpRight size={12} /></Link>}>{documents.length ? <div className="section-table">{documents.slice(0, 8).map((item) => { const due = Number(item.total) - Number(item.paid); return <Link href="/documents" className="section-row dashboard-document" key={item.id}><span className="document-icon"><FileText size={15} /></span><span><b>{item.number}</b><small>{item.contact_name}</small></span><span><strong>{money(item.total)}</strong><small>{due > 0 ? `${money(due)} due` : 'Paid in full'}</small></span><ArrowUpRight size={14} /></Link>; })}</div> : <Empty icon={FileText} title="No records yet" text="Create a contact, product and order to begin." />}</Panel><Panel eyebrow="BUSINESS PULSE" title="Collection health" className="health-panel"><div className="collection-visual"><div className="collection-ring" style={{ '--progress': `${collectionRate * 3.6}deg` }}><span><strong>{collectionRate}%</strong><small>collected</small></span></div><div><small>RECEIVED</small><strong>{money(collected, 0)}</strong><p>of {money(billed, 0)} billed</p></div></div><div className="health-list"><div className="insight-line"><span><i className="health-dot is-live" /> Live updates</span><strong>Enabled</strong></div><div className="insight-line"><span><i className="health-dot" /> Access level</span><strong>{user.role}</strong></div><div className="insight-line"><span><i className="health-dot" /> Activity events</span><strong>{data.audit?.length || 0}</strong></div></div><Activity className="panel-watermark" /></Panel></section>
  </>;
}
