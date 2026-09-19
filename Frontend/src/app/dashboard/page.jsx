'use client';

import { useEffect, useMemo, useState } from 'react';
import { Activity, BarChart3, FileText, LayoutDashboard, LogOut, Menu, Moon, ReceiptIndianRupee, Settings, Sun, Users, WalletCards, X } from 'lucide-react';

const roleDetails = {
  admin: { label: 'Admin workspace', eyebrow: 'ADMIN CONTROL CENTRE', title: 'Lead the whole business.', copy: 'Manage people, company identity, records and financial controls from one secure workspace.' },
  accountant: { label: 'Accountant workspace', eyebrow: 'ACCOUNTING DESK', title: 'Keep every number moving.', copy: 'Record sales, purchasing, payments, expenses and reports with a clean operational view.' },
  contact: { label: 'Partner portal', eyebrow: 'PARTNER PORTAL', title: 'Your business, in one place.', copy: 'Review linked invoices and bills, submit payment details, and follow every receipt.' },
};

const nav = [
  ['Overview', LayoutDashboard], ['Invoices & bills', FileText], ['Contacts', Users], ['Products', ReceiptIndianRupee], ['Payments', WalletCards], ['Reports', BarChart3], ['Activity', Activity], ['Settings', Settings],
];

function money(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format((value || 0) / 100); }

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [data, setData] = useState(null);
  const [dark, setDark] = useState(false);
  const [menu, setMenu] = useState(false);
  const [error, setError] = useState('');

  async function load() {
    try {
      const session = await fetch('/api/session', { credentials: 'include' }).then((r) => r.json());
      if (!session.user) { window.location.href = '/login'; return; }
      setUser(session.user);
      const result = await fetch('/api/data', { credentials: 'include' }).then((r) => r.json());
      setData(result);
    } catch (err) { setError(err.message || 'Unable to load workspace.'); }
  }

  useEffect(() => { setDark(localStorage.getItem('urban-theme') === 'dark'); load(); }, []);
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('urban-theme', dark ? 'dark' : 'light'); }, [dark]);

  const role = roleDetails[user?.role] || roleDetails.admin;
  const documents = data?.documents || [];
  const unpaid = useMemo(() => documents.filter((item) => item.paid < item.total).length, [documents]);

  if (error) return <main className="next-error"><h1>Unable to open workspace</h1><p>{error}</p><button onClick={load}>Try again</button></main>;
  if (!user || !data) return <main className="next-loading"><div className="loading-mark">UF</div><p>Opening your workspace…</p></main>;

  return <div className="next-shell">
    {menu && <button className="next-overlay" aria-label="Close navigation" onClick={() => setMenu(false)} />}
    <aside className={`next-sidebar ${menu ? 'is-open' : ''}`}>
      <div className="next-brand"><span>UF</span><div>Urban Furniture<small>BOOKS & BUSINESS</small></div><button className="mobile-close" onClick={() => setMenu(false)}><X size={18} /></button></div>
      <div className="next-workspace"><span>◈</span><div><strong>Urban Furniture</strong><small>{role.label}</small></div></div>
      <p className="next-nav-label">Workspace</p>
      <nav>{nav.filter(([label]) => user.role !== 'contact' || ['Overview', 'Invoices & bills', 'Payments', 'Settings'].includes(label)).map(([label, Icon], index) => <button key={label} className={index === 0 ? 'active' : ''} onClick={() => setMenu(false)}><Icon size={16} />{label}{label === 'Invoices & bills' && unpaid > 0 && <b>{unpaid}</b>}</button>)}</nav>
      <div className="next-sidebar-bottom"><div className="next-help"><small>CONNECTED WORKSPACE</small><strong>Live financial records</strong><p>Every committed change stays visible to the right people.</p></div><div className="next-user"><span>{user.name?.slice(0, 2).toUpperCase() || 'UF'}</span><div><strong>{user.name}</strong><small>{role.label}</small></div><button onClick={async () => { await fetch('/api/logout', { method: 'POST', credentials: 'include' }); window.location.href = '/'; }}><LogOut size={15} /></button></div></div>
    </aside>
    <main className="next-main">
      <header className="next-topbar"><button className="menu-button" onClick={() => setMenu(true)}><Menu size={18} /></button><div><small>Workspace / {role.label}</small><h1>Overview</h1></div><div className="next-actions"><button className="theme-button" aria-label="Toggle theme" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={16} /> : <Moon size={16} />}{dark ? 'Light' : 'Dark'}</button><span className="live-pill"><i /> Live</span><span className="currency-pill">INR</span></div></header>
      <section className="next-content"><section className="role-hero"><div><small>{role.eyebrow}</small><h2>{role.title}</h2><p>{role.copy}</p></div><div className="hero-actions"><button>Open {user.role === 'contact' ? 'invoices' : 'reports'}</button><button className="soft-button">View activity</button></div></section>
        <section className="next-metrics"><article><span>Open documents</span><strong>{documents.length}</strong><small>Invoices and bills</small></article><article className="featured"><span>Outstanding</span><strong>{money(documents.reduce((sum, item) => sum + item.total - item.paid, 0))}</strong><small>Current balance across documents</small></article><article><span>Payment activity</span><strong>{data.payments?.length || 0}</strong><small>Recorded settlements</small></article><article><span>Workspace status</span><strong>Live</strong><small>PostgreSQL connected</small></article></section>
        <section className="next-grid"><article className="next-card"><div className="card-heading"><div><small>REAL DATA</small><h3>Recent invoices & bills</h3></div><span>{documents.length} records</span></div>{documents.length ? <div className="next-table">{documents.slice(0, 6).map((item) => <div key={item.id}><span><b>{item.number}</b><small>{item.contact_name}</small></span><strong>{money(item.total)}</strong></div>)}</div> : <div className="next-empty"><FileText size={22} /><strong>No business records yet</strong><p>Add your first contact, product or order to start the workspace.</p></div>}</article><article className="next-card next-insight"><div className="card-heading"><div><small>ROLE GUIDANCE</small><h3>{user.role === 'admin' ? 'Control centre' : user.role === 'accountant' ? 'Accounting desk' : 'Partner actions'}</h3></div><Activity size={17} /></div><div className="insight-line"><span>Database</span><strong>{data.database || 'PostgreSQL'}</strong></div><div className="insight-line"><span>Realtime updates</span><strong>Connected</strong></div><div className="insight-line"><span>Access scope</span><strong>{role.label}</strong></div></article></section>
      </section>
    </main>
  </div>;
}
