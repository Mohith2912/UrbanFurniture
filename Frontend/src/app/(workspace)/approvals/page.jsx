'use client';

import { FileCheck2 } from 'lucide-react';
import { useState } from 'react';
import { send } from '@/lib/api';
import { dateText, money } from '@/lib/format';
import { Empty, FormMessage, PageIntro, Panel, Status } from '@/components/page-ui';
import { useWorkspace } from '@/components/workspace-provider';

export default function ApprovalsPage() {
  const { data, refresh } = useWorkspace(); const [error, setError] = useState('');
  const requests = data.payment_requests || [];
  async function review(id, decision) { setError(''); try { await send(`/payment-requests/${id}/review`, 'POST', { decision, note: decision === 'rejected' ? 'Payment details could not be verified.' : '' }); await refresh(); } catch (err) { setError(err.message); } }
  return <><PageIntro eyebrow="VERIFICATION QUEUE" title="Payment approvals" description="Verify customer payment details before the backend posts a receipt and changes the invoice balance." /><FormMessage error={error} /><Panel eyebrow="PAYMENT REQUESTS" title="Submitted payments" meta={`${requests.length} requests`}>{requests.length ? <div className="section-table">{requests.map((item) => <div className="section-row order-row" key={item.id}><span><b>{item.document_number} · {item.contact_name}</b><small>{dateText(item.date)} · {item.method} · {item.reference}</small></span><span><strong>{money(item.amount)}</strong><small>{money(item.outstanding)} invoice balance</small></span><Status tone={item.status === 'approved' ? 'green' : item.status === 'rejected' ? 'red' : 'amber'}>{item.status}</Status>{item.status === 'pending' && <span className="row-actions"><button className="next-primary compact" onClick={() => review(item.id, 'approved')}>Approve</button><button className="soft-link" onClick={() => review(item.id, 'rejected')}>Reject</button></span>}</div>)}</div> : <Empty icon={FileCheck2} title="Nothing to review" text="Customer payment submissions will appear here." />}</Panel></>;
}
