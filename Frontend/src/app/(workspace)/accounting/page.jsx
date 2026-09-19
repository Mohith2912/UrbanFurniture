'use client';

import { Calculator } from 'lucide-react';
import { useState } from 'react';
import { useWorkspace } from '@/components/workspace-provider';
import { Empty, PageIntro, Panel, Status } from '@/components/page-ui';
import { dateText, money } from '@/lib/format';

export default function AccountingPage() {
  const { data } = useWorkspace(); const [tab, setTab] = useState('entries');
  const entries = data.entries || []; const accounts = data.accounts || []; const journals = data.journals || [];
  return <><PageIntro eyebrow="DOUBLE ENTRY LEDGER" title="Accounting" description="Review posted entries, the chart of accounts and journals that control automatic postings." /><div className="section-tabs">{[['entries', 'Journal entries'], ['accounts', 'Chart of accounts'], ['journals', 'Journals']].map(([key, label]) => <button className={tab === key ? 'active' : ''} onClick={() => setTab(key)} key={key}>{label}</button>)}</div><Panel eyebrow="ACCOUNTING RECORDS" title={tab === 'entries' ? 'Journal entries' : tab === 'accounts' ? 'Chart of accounts' : 'Journals'} meta={`${data[tab]?.length || 0} records`}>{tab === 'entries' ? (entries.length ? <div className="section-table">{entries.map((entry) => <div className="section-row" key={entry.id}><span><b>{entry.number}</b><small>{dateText(entry.date)} · {entry.journal_name} · {entry.reference}</small></span><span><strong>{money(entry.total)}</strong><Status tone={entry.source === 'manual' ? 'amber' : 'green'}>{entry.source}</Status></span></div>)}</div> : <Empty icon={Calculator} title="No journal entries" text="Posting documents and payments creates balanced entries automatically." />) : tab === 'accounts' ? <div className="data-grid">{accounts.map((account) => <article className="record-card" key={account.id}><div><strong>{account.code} · {account.name}</strong><small>{account.type}</small></div><Status tone={account.active ? 'green' : 'red'}>{account.active ? 'Active' : 'Archived'}</Status><p>{account.system_key ? 'Protected system account' : 'Configurable account'}</p></article>)}</div> : <div className="data-grid">{journals.map((journal) => <article className="record-card" key={journal.id}><div><strong>{journal.name}</strong><small>{journal.type}</small></div><Status tone={journal.active ? 'green' : 'red'}>{journal.active ? 'Active' : 'Archived'}</Status><p>Default debit #{journal.debit_account_id} · credit #{journal.credit_account_id}</p></article>)}</div>}</Panel></>;
}
