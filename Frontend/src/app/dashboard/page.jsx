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

const sectionKeys = {
  Overview: 'overview', 'Invoices & bills': 'documents', Contacts: 'contacts', Products: 'products',
  Payments: 'payments', Reports: 'reports', Activity: 'activity', Settings: 'settings',
};

function dateText(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function valueText(value) {
  if (value === null || value === undefined || value === '') return '—';
  return String(value);
}

function SectionView({ section, data, user, money }) {
  const documents = data?.documents || [];
  const payments = data?.payments || [];
  const contacts = data?.contacts || [];
  const products = data?.products || [];
  const orders = data?.orders || [];
  const audit = data?.audit || [];
  if (section === 'overview') return null;
  if (section === 'documents') return <section className="next-card section-card"><div className="card-heading"><div><small>LIVE RECORDS</small><h3>Invoices and bills</h3></div><span>{documents.length} records</span></div>{documents.length ? <div className="section-table">{documents.map((item) => <div className="section-row" key={item.id}><span><b>{valueText(item.number)}</b><small>{valueText(item.contact_name)} · {dateText(item.date)}</small></span><span><strong>{money(item.total)}</strong><small>{valueText(item.status || 'open')}</small></span></div>)}</div> : <EmptyState icon={FileText} title="No invoices or bills yet" text="Create a sales or purchase order in the accounting workspace." />}</section>;
  if (section === 'contacts') return <section className="next-card section-card"><div className="card-heading"><div><small>MASTER DATA</small><h3>Contacts</h3></div><span>{contacts.length} records</span></div>{contacts.length ? <div className="section-table">{contacts.map((item) => <div className="section-row" key={item.id}><span><b>{valueText(item.name)}</b><small>{valueText(item.email || item.phone)}</small></span><span><strong>{valueText(item.kind || 'Customer')}</strong><small>{valueText(item.gstin || 'GST not set')}</small></span></div>)}</div> : <EmptyState icon={Users} title="No contacts yet" text="Add customers and vendors from the classic workspace." />}</section>;
  if (section === 'products') return <section className="next-card section-card"><div className="card-heading"><div><small>MASTER DATA</small><h3>Products and services</h3></div><span>{products.length} records</span></div>{products.length ? <div className="section-table">{products.map((item) => <div className="section-row" key={item.id}><span><b>{valueText(item.name)}</b><small>{valueText(item.category || item.type)}</small></span><span><strong>{money(item.sale_price || item.cost)}</strong><small>{item.type === 'Service' ? 'Service' : 'Stock item'}</small></span></div>)}</div> : <EmptyState icon={ReceiptIndianRupee} title="No products yet" text="Add your first product or service before creating an order." />}</section>;
  if (section === 'payments') return <section className="next-card section-card"><div className="card-heading"><div><small>SETTLEMENTS</small><h3>Payments</h3></div><span>{payments.length} records</span></div>{payments.length ? <div className="section-table">{payments.map((item) => <div className="section-row" key={item.id}><span><b>{valueText(item.document_number)}</b><small>{valueText(item.contact_name)} · {dateText(item.date)}</small></span><span><strong>{money(item.amount)}</strong><small>{valueText(item.method || 'Payment')}</small></span></div>)}</div> : <EmptyState icon={WalletCards} title="No payments yet" text="Payments appear here after an invoice or bill is settled." />}</section>;
  if (section === 'reports') return <section className="section-grid"><article className="next-card"><div className="card-heading"><div><small>FINANCIAL CONTROL</small><h3>Reports</h3></div><BarChart3 size={17} /></div><div className="insight-line"><span>Orders</span><strong>{orders.length}</strong></div><div className="insight-line"><span>Open documents</span><strong>{documents.filter((item) => Number(item.paid || 0) < Number(item.total || 0)).length}</strong></div><div className="insight-line"><span>Payments recorded</span><strong>{payments.length}</strong></div><div className="insight-line"><span>Database</span><strong>{valueText(data.database)}</strong></div></article><article className="next-card"><div className="card-heading"><div><small>ACCESS</small><h3>Available reports</h3></div></div><p className="section-copy">Use the accounting workspace for balance sheet, profit and loss, stock, budget and ledger exports.</p><button className="next-primary" onClick={() => { window.location.href = '/'; }}>Open reports workspace</button></article></section>;
  if (section === 'activity') return <section className="next-card section-card"><div className="card-heading"><div><small>AUDIT TRAIL</small><h3>Recent activity</h3></div><span>{audit.length} events</span></div>{audit.length ? <div className="section-table">{audit.slice(0, 30).map((item) => <div className="section-row" key={item.id}><span><b>{valueText(item.action)}</b><small>{valueText(item.user_name || user.name)} · {dateText(item.created_at || item.date)}</small></span><span><strong>{valueText(item.entity_type)}</strong><small>{valueText(item.entity_id)}</small></span></div>)}</div> : <EmptyState icon={Activity} title="No activity yet" text="New records and changes will appear here." />}</section>;
  return <section className="next-card section-card"><div className="card-heading"><div><small>WORKSPACE</small><h3>Settings</h3></div><Settings size={17} /></div><div className="insight-line"><span>Signed in as</span><strong>{valueText(user.email)}</strong></div><div className="insight-line"><span>Role</span><strong>{valueText(user.role)}</strong></div><div className="insight-line"><span>Company</span><strong>{valueText(data.workspace?.company_name || 'Urban Furniture')}</strong></div><div className="insight-line"><span>Theme</span><strong>Use the button in the top bar</strong></div><p className="section-copy">Company profile, account management, backups and password changes are available in the accounting workspace.</p><button className="next-primary" onClick={() => { window.location.href = '/'; }}>Open full settings</button></section>;
}

function EmptyState({ icon: Icon, title, text }) { return <div className="next-empty"><Icon size={22} /><strong>{title}</strong><p>{text}</p></div>; }

function money(value) { return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format((value || 0) / 100); }

export default function Dashboard() {
  const [user, setUser] = useState(null);
  const [data, setData] = useState(null);
  const [dark, setDark] = useState(false);
  const [menu, setMenu] = useState(false);
  const [section, setSection] = useState('overview');
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
  const title = Object.entries(sectionKeys).find(([, key]) => key === section)?.[0] || 'Overview';
  const canSee = (label) => user?.role !== 'contact' || ['Overview', 'Invoices & bills', 'Payments', 'Settings'].includes(label);

  if (error) return <main className="next-error"><h1>Unable to open workspace</h1><p>{error}</p><button onClick={load}>Try again</button></main>;
  if (!user || !data) return <main className="next-loading"><div className="loading-mark">UF</div><p>Opening your workspace…</p></main>;

  return <div className="next-shell">
    {menu && <button className="next-overlay" aria-label="Close navigation" onClick={() => setMenu(false)} />}
    <aside className={`next-sidebar ${menu ? 'is-open' : ''}`}>
      <div className="next-brand"><span>UF</span><div>Urban Furniture<small>BOOKS & BUSINESS</small></div><button className="mobile-close" onClick={() => setMenu(false)}><X size={18} /></button></div>
      <div className="next-workspace"><span>◈</span><div><strong>Urban Furniture</strong><small>{role.label}</small></div></div>
      <p className="next-nav-label">Workspace</p>
      <nav>{nav.filter(([label]) => canSee(label)).map(([label, Icon]) => <button key={label} className={sectionKeys[label] === section ? 'active' : ''} onClick={() => { setSection(sectionKeys[label]); setMenu(false); }}><Icon size={16} />{label}{label === 'Invoices & bills' && unpaid > 0 && <b>{unpaid}</b>}</button>)}</nav>
      <div className="next-sidebar-bottom"><div className="next-help"><small>CONNECTED WORKSPACE</small><strong>Live financial records</strong><p>Every committed change stays visible to the right people.</p></div><div className="next-user"><span>{user.name?.slice(0, 2).toUpperCase() || 'UF'}</span><div><strong>{user.name}</strong><small>{role.label}</small></div><button onClick={async () => { await fetch('/api/logout', { method: 'POST', credentials: 'include' }); window.location.href = '/'; }}><LogOut size={15} /></button></div></div>
    </aside>
    <main className="next-main">
      <header className="next-topbar"><button className="menu-button" onClick={() => setMenu(true)}><Menu size={18} /></button><div><small>Workspace / {role.label}</small><h1>{title}</h1></div><div className="next-actions"><button className="theme-button" aria-label="Toggle theme" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={16} /> : <Moon size={16} />}{dark ? 'Light' : 'Dark'}</button><span className="live-pill"><i /> Live</span><span className="currency-pill">INR</span></div></header>
      <section className="next-content"><section className="role-hero"><div><small>{role.eyebrow}</small><h2>{section === 'overview' ? role.title : title}</h2><p>{section === 'overview' ? role.copy : `Review your ${title.toLowerCase()} using live records from the accounting database.`}</p></div><div className="hero-actions"><button onClick={() => setSection(user.role === 'contact' ? 'documents' : 'reports')}>Open {user.role === 'contact' ? 'invoices' : 'reports'}</button><button className="soft-button" onClick={() => setSection(user.role === 'contact' ? 'documents' : 'activity')}>{user.role === 'contact' ? 'View invoices' : 'View activity'}</button></div></section>
        {section !== 'overview' && <SectionView section={section} data={data} user={user} money={money} />}
        {section === 'overview' && <>
        <section className="next-metrics"><article><span>Open documents</span><strong>{documents.length}</strong><small>Invoices and bills</small></article><article className="featured"><span>Outstanding</span><strong>{money(documents.reduce((sum, item) => sum + item.total - item.paid, 0))}</strong><small>Current balance across documents</small></article><article><span>Payment activity</span><strong>{data.payments?.length || 0}</strong><small>Recorded settlements</small></article><article><span>Workspace status</span><strong>Live</strong><small>PostgreSQL connected</small></article></section>
        <section className="next-grid"><article className="next-card"><div className="card-heading"><div><small>REAL DATA</small><h3>Recent invoices & bills</h3></div><span>{documents.length} records</span></div>{documents.length ? <div className="next-table">{documents.slice(0, 6).map((item) => <div key={item.id}><span><b>{item.number}</b><small>{item.contact_name}</small></span><strong>{money(item.total)}</strong></div>)}</div> : <EmptyState icon={FileText} title="No business records yet" text="Add your first contact, product or order to start the workspace." />}</article><article className="next-card next-insight"><div className="card-heading"><div><small>ROLE GUIDANCE</small><h3>{user.role === 'admin' ? 'Control centre' : user.role === 'accountant' ? 'Accounting desk' : 'Partner actions'}</h3></div><Activity size={17} /></div><div className="insight-line"><span>Database</span><strong>{data.database || 'PostgreSQL'}</strong></div><div className="insight-line"><span>Realtime updates</span><strong>Connected</strong></div><div className="insight-line"><span>Access scope</span><strong>{role.label}</strong></div></article></section>
        </>}
      </section>
    </main>
  </div>;
}
