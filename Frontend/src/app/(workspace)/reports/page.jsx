'use client';

import { useEffect, useState } from 'react';
import { BarChart3, Download } from 'lucide-react';
import { api } from '@/lib/api';
import { money, today } from '@/lib/format';
import { Empty, FormMessage, PageIntro, Panel } from '@/components/page-ui';

export default function ReportsPage() {
  const now = new Date();
  const [start, setStart] = useState(`${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}-01`);
  const [end, setEnd] = useState(today());
  const [report, setReport] = useState(null);
  const [error, setError] = useState('');
  async function load() { try { setReport(await api(`/reports?start=${start}&end=${end}`)); setError(''); } catch (err) { setError(err.message); } }
  useEffect(() => { load(); }, []);
  const metrics = report ? [{ name: 'Revenue', value: report.income }, { name: 'Expenses', value: report.expenses }, { name: 'Net profit', value: report.profit }, { name: 'Assets', value: report.assets }] : [];
  return <><PageIntro eyebrow="FINANCIAL REPORTING" title="Reports" description="Review profit, balance, budgets, stock and ledger results calculated from posted entries." action={<a className="next-primary compact" href={`/api/reports/export?kind=ledger&start=${start}&end=${end}`}><Download size={15} /> Export ledger</a>} />
    <form className="report-filter" onSubmit={(e) => { e.preventDefault(); load(); }}><label>From<input type="date" value={start} onChange={(e) => setStart(e.target.value)} /></label><label>To<input type="date" value={end} onChange={(e) => setEnd(e.target.value)} /></label><button className="next-primary compact">Apply period</button></form><FormMessage error={error} />
    {report ? <><section className="next-metrics">{metrics.map((metric, index) => <article className={index === 2 ? 'featured' : ''} key={metric.name}><span>{metric.name}</span><strong>{money(metric.value, 0)}</strong><small>{start} to {end}</small></article>)}</section><section className="section-grid"><Panel eyebrow="PROFIT AND LOSS" title="Income and expenses"><div className="insight-line"><span>Income</span><strong>{money(report.income)}</strong></div><div className="insight-line"><span>Expenses</span><strong>{money(report.expenses)}</strong></div><div className="insight-line"><span>Net result</span><strong>{money(report.profit)}</strong></div></Panel><Panel eyebrow="BALANCE SHEET" title="Assets and funding"><div className="insight-line"><span>Assets</span><strong>{money(report.assets)}</strong></div><div className="insight-line"><span>Liabilities</span><strong>{money(report.liabilities)}</strong></div><div className="insight-line"><span>Capital and earnings</span><strong>{money(report.capital + report.earnings)}</strong></div><div className="insight-line"><span>Balance difference</span><strong>{money(report.balance_difference)}</strong></div></Panel></section><Panel eyebrow="GENERAL LEDGER" title="Recent ledger lines" meta={`${report.ledger.length} lines`}>{report.ledger.length ? <div className="section-table">{report.ledger.slice(0, 50).map((line, index) => <div className="section-row" key={`${line.number}-${line.code}-${index}`}><span><b>{line.number} · {line.account}</b><small>{line.date} · {line.reference}</small></span><span><strong>{line.debit ? `Debit ${money(line.debit)}` : `Credit ${money(line.credit)}`}</strong></span></div>)}</div> : <Empty icon={BarChart3} title="No ledger activity" text="Post an invoice, bill, payment or journal entry in this period." />}</Panel></> : <main className="next-loading compact-loading"><p>Calculating reports…</p></main>}
  </>;
}
