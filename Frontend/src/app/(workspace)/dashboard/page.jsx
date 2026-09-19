'use client';

import Link from 'next/link';
import { Activity, FileText } from 'lucide-react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel } from '@/components/page-ui';
import { money } from '@/lib/format';

export default function DashboardPage() {
  const { user, data } = useWorkspace();
  const documents = data.documents || [];
  const outstanding = documents.reduce((sum, item) => sum + Number(item.total || 0) - Number(item.paid || 0), 0);
  const roleCopy = user.role === 'admin' ? 'Manage the whole company, financial controls and access from one secure workspace.' : user.role === 'accountant' ? 'Keep sales, purchases, payments and reports moving from one accounting desk.' : 'Review your invoices, balances and payment history.';
  return <><PageIntro eyebrow={user.role === 'contact' ? 'PARTNER PORTAL' : 'BUSINESS CONTROL CENTRE'} title={`Welcome, ${user.name}.`} description={roleCopy} action={<><Link className="next-primary compact" href="/documents">View invoices</Link>{user.role !== 'contact' && <Link className="soft-link" href="/orders">Create order</Link>}</>} />
    <section className="next-metrics"><article><span>Documents</span><strong>{documents.length}</strong><small>Invoices and bills</small></article><article className="featured"><span>Outstanding</span><strong>{money(outstanding, 0)}</strong><small>Current balance</small></article><article><span>Payments</span><strong>{data.payments?.length || 0}</strong><small>Recorded settlements</small></article><article><span>Database</span><strong>Live</strong><small>{data.database}</small></article></section>
    <section className="next-grid"><Panel eyebrow="RECENT RECORDS" title="Invoices and bills" meta={`${documents.length} records`}>{documents.length ? <div className="section-table">{documents.slice(0, 8).map((item) => <Link href="/documents" className="section-row" key={item.id}><span><b>{item.number}</b><small>{item.contact_name}</small></span><span><strong>{money(item.total)}</strong><small>{money(item.total - item.paid)} due</small></span></Link>)}</div> : <Empty icon={FileText} title="No records yet" text="Create a contact, product and order to begin." />}</Panel><Panel eyebrow="WORKSPACE HEALTH" title="Connected services"><div className="insight-line"><span>Database</span><strong>{data.database}</strong></div><div className="insight-line"><span>Live updates</span><strong>Enabled</strong></div><div className="insight-line"><span>Access</span><strong>{user.role}</strong></div><div className="insight-line"><span>Activity events</span><strong>{data.audit?.length || 0}</strong></div><Activity className="panel-watermark" /></Panel></section>
  </>;
}
