'use client';

import { useState } from 'react';
import { Plus, ReceiptIndianRupee } from 'lucide-react';
import { send } from '@/lib/api';
import { dateText, money, today } from '@/lib/format';
import { Empty, FormMessage, Modal, PageIntro, Panel } from '@/components/page-ui';
import { useWorkspace } from '@/components/workspace-provider';

export default function ExpensesPage() {
  const { data, refresh } = useWorkspace();
  const [open, setOpen] = useState(false); const [error, setError] = useState('');
  const expenses = data.expenses || [];
  async function submit(event) { event.preventDefault(); setError(''); try { await send('/expenses', 'POST', Object.fromEntries(new FormData(event.currentTarget))); await refresh(); setOpen(false); } catch (err) { setError(err.message); } }
  return <><PageIntro eyebrow="OPERATING COSTS" title="Expenses" description="Record paid business costs with an automatic balanced accounting entry." action={<button className="next-primary compact" onClick={() => setOpen(true)}><Plus size={15} /> Record expense</button>} /><Panel eyebrow="EXPENSE REGISTER" title="Posted expenses" meta={`${expenses.length} records`}>{expenses.length ? <div className="section-table">{expenses.map((item) => <div className="section-row" key={item.id}><span><b>{item.number} · {item.name}</b><small>{item.account_name} · {item.method}</small></span><span><strong>{money(item.amount)}</strong><small>{dateText(item.date)}</small></span></div>)}</div> : <Empty icon={ReceiptIndianRupee} title="No expenses yet" text="Record rent, utilities or another paid operating cost." />}</Panel>{open && <Modal title="Record expense" onClose={() => setOpen(false)}><form className="next-form-grid" onSubmit={submit}><label className="full">Description<input name="name" required /></label><label>Date<input name="date" type="date" defaultValue={today()} required /></label><label>Amount<input name="amount" type="number" min="0.01" step="0.01" required /></label><label>Paid through<select name="method"><option>Bank</option><option>Cash</option></select></label><label>Expense account<select name="account_id" required><option value="">Select account</option>{(data.accounts || []).filter((a) => a.type === 'Expense' && a.active).map((a) => <option key={a.id} value={a.id}>{a.code} · {a.name}</option>)}</select></label><label>Analytic account<select name="analytic_id"><option value="">None</option>{(data.analytics || []).filter((a) => a.type === 'Expense' && a.active).map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}</select></label><label>Reference<input name="reference" /></label><FormMessage error={error} /><div className="dialog-actions full"><button type="button" className="soft-link" onClick={() => setOpen(false)}>Cancel</button><button className="next-primary compact">Save expense</button></div></form></Modal>}</>;
}
