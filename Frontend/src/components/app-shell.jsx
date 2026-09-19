'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { LogOut, Menu, Moon, Sun, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getSession } from '@/lib/api';
import { navigation, roleLabel } from '@/lib/navigation';
import { useWorkspace } from './workspace-provider';

export default function AppShell({ children }) {
  const { user, data, live } = useWorkspace();
  const pathname = usePathname();
  const [menu, setMenu] = useState(false);
  const [dark, setDark] = useState(false);
  useEffect(() => setDark(localStorage.getItem('urban-theme') === 'dark'), []);
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('urban-theme', dark ? 'dark' : 'light'); }, [dark]);
  const links = navigation.filter((item) => item.roles.includes(user.role));
  const current = links.find((item) => pathname.startsWith(item.href));
  const allowedPath = Boolean(current);
  useEffect(() => {
    if (!allowedPath) window.location.replace('/dashboard');
  }, [allowedPath]);
  async function logout() {
    const session = await getSession();
    await fetch('/api/logout', { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf }, body: '{}' });
    window.location.href = '/login';
  }
  return <div className="next-shell">
    {menu && <button className="next-overlay" aria-label="Close navigation" onClick={() => setMenu(false)} />}
    <aside className={`next-sidebar ${menu ? 'is-open' : ''}`}>
      <div className="next-brand"><span>UF</span><div>Urban Furniture<small>BOOKS & BUSINESS</small></div><button className="mobile-close" onClick={() => setMenu(false)}><X size={18} /></button></div>
      <div className="next-workspace"><span>◈</span><div><strong>{data.workspace?.company_name || 'Urban Furniture'}</strong><small>{roleLabel[user.role]}</small></div></div>
      <p className="next-nav-label">Workspace</p>
      <nav>{links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={pathname === href ? 'active' : ''} onClick={() => setMenu(false)}><Icon size={16} />{label}{label === 'Invoices & bills' && data.documents?.filter((d) => d.paid < d.total).length > 0 && <b>{data.documents.filter((d) => d.paid < d.total).length}</b>}</Link>)}</nav>
      <div className="next-sidebar-bottom"><div className="next-help"><small>CONNECTED WORKSPACE</small><strong>{data.database}</strong><p>Every saved change is shared with the right people.</p></div><div className="next-user"><span>{user.name?.slice(0, 2).toUpperCase()}</span><div><strong>{user.name}</strong><small>{roleLabel[user.role]}</small></div><button onClick={logout} aria-label="Sign out"><LogOut size={15} /></button></div></div>
    </aside>
    <main className="next-main"><header className="next-topbar"><button className="menu-button" onClick={() => setMenu(true)}><Menu size={18} /></button><div><small>Workspace / {roleLabel[user.role]}</small><h1>{current?.label || 'Workspace'}</h1></div><div className="next-actions"><button className="theme-button" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={16} /> : <Moon size={16} />}{dark ? 'Light' : 'Dark'}</button><span className={`live-pill ${live ? '' : 'is-offline'}`}><i /> {live ? 'Live' : 'Connecting'}</span><span className="currency-pill">INR</span></div></header><section className="next-content">{children}</section></main>
  </div>;
}
