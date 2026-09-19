'use client';

import { WalletCards } from 'lucide-react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel, Status } from '@/components/page-ui';
import { dateText, money } from '@/lib/format';

export default function PaymentsPage() {
  const { data, user } = useWorkspace();
  const payments = data.payments || [];
  const requests = data.payment_requests || [];
  return <><PageIntro eyebrow="MONEY MOVEMENT" title="Payments" description="Review receipts and vendor payments linked to their original invoices and bills." />
    <section className="next-metrics"><article><span>Payments</span><strong>{payments.length}</strong><small>Completed entries</small></article><article className="featured"><span>Total recorded</span><strong>{money(payments.reduce((sum, p) => sum + Number(p.amount || 0), 0), 0)}</strong><small>Across all visible records</small></article><article><span>Pending checks</span><strong>{requests.filter((r) => r.status === 'pending').length}</strong><small>Awaiting verification</small></article><article><span>Access</span><strong>{user.role}</strong><small>Role-scoped records</small></article></section>
    <Panel eyebrow="PAYMENT REGISTER" title="Payment history" meta={`${payments.length} records`}>{payments.length ? <div className="section-table">{payments.map((p) => <div className="section-row" key={p.id}><span><b>{p.number}</b><small>{p.document_number} · {p.contact_name}</small></span><span><strong>{money(p.amount)}</strong><small>{dateText(p.date)} · {p.method}</small></span></div>)}</div> : <Empty icon={WalletCards} title="No payments yet" text="Record a settlement from an open invoice or bill." />}</Panel>
    {requests.length > 0 && <Panel eyebrow="PAYMENT REQUESTS" title="Submitted payment details" meta={`${requests.length} requests`}>{requests.map((r) => <div className="section-row" key={r.id}><span><b>{r.document_number}</b><small>{r.contact_name} · {r.reference}</small></span><span><strong>{money(r.amount)}</strong><Status tone={r.status === 'approved' ? 'green' : r.status === 'rejected' ? 'red' : 'amber'}>{r.status}</Status></span></div>)}</Panel>}
  </>;
}
