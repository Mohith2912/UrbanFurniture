'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Bell, ChevronRight, LogOut, Menu, Moon, Search, Sun, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getSession, send } from '@/lib/api';
import { navigation, roleLabel } from '@/lib/navigation';
import Brand from './brand';
import { useWorkspace } from './workspace-provider';

export default function AppShell({ children }) {
  const { user, data, live } = useWorkspace();
  const pathname = usePathname();
  const [menu, setMenu] = useState(false);
  const [dark, setDark] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const [logoutError, setLogoutError] = useState('');
  useEffect(() => setDark(localStorage.getItem('urban-theme') === 'dark'), []);
  useEffect(() => { document.documentElement.dataset.theme = dark ? 'dark' : 'light'; localStorage.setItem('urban-theme', dark ? 'dark' : 'light'); }, [dark]);
  const links = navigation.filter((item) => item.roles.includes(user.role));
  const current = links.find((item) => pathname.startsWith(item.href));
  const allowedPath = Boolean(current);
  useEffect(() => {
    if (!allowedPath) window.location.replace('/dashboard');
  }, [allowedPath]);
  async function logout() {
    if (loggingOut) return;
    setLoggingOut(true);
    setLogoutError('');
    try {
      await getSession();
      await send('/logout', 'POST', {});
      window.location.replace('/login');
    } catch (err) {
      setLogoutError(err.message || 'Unable to log out. Please try again.');
      setLoggingOut(false);
    }
  }
  return <div className="next-shell">
    {menu && <button className="next-overlay" aria-label="Close navigation" onClick={() => setMenu(false)} />}
    <aside className={`next-sidebar ${menu ? 'is-open' : ''}`}>
      <div className="sidebar-brand"><Brand inverse /><button className="mobile-close" onClick={() => setMenu(false)} aria-label="Close navigation"><X size={18} /></button></div>
      <div className="next-workspace"><span className="workspace-monogram">UF</span><div><strong>{data.workspace?.company_name || 'Urban Furniture'}</strong><small>{roleLabel[user.role]}</small></div><ChevronRight size={14} /></div>
      <p className="next-nav-label">Workspace</p>
      <nav>{links.map(({ href, label, icon: Icon }) => <Link key={href} href={href} className={pathname === href ? 'active' : ''} onClick={() => setMenu(false)}><Icon size={16} />{label}{label === 'Invoices & bills' && data.documents?.filter((d) => d.paid < d.total).length > 0 && <b>{data.documents.filter((d) => d.paid < d.total).length}</b>}</Link>)}</nav>
      <div className="next-sidebar-bottom"><div className="next-help"><span className="connection-orbit"><i /></span><div><small>LIVE WORKSPACE</small><strong>{data.database}</strong><p>Changes sync automatically for your team.</p></div></div><div className="next-user"><span>{user.name?.slice(0, 2).toUpperCase()}</span><div><strong>{user.name}</strong><small>{roleLabel[user.role]}</small></div></div><button className="logout-button" type="button" onClick={logout} disabled={loggingOut} aria-busy={loggingOut}><LogOut size={16} aria-hidden="true" />{loggingOut ? 'Logging out…' : 'Log out'}</button>{logoutError && <p className="logout-error" role="alert">{logoutError}</p>}</div>
    </aside>
    <main className="next-main"><header className="next-topbar"><div className="topbar-title"><button className="menu-button" onClick={() => setMenu(true)} aria-label="Open navigation"><Menu size={18} /></button><div><small>Urban Furniture <ChevronRight size={10} /> {roleLabel[user.role]}</small><h1>{current?.label || 'Workspace'}</h1></div></div><div className="next-actions"><div className="topbar-search"><Search size={15} /><span>Quick find</span><kbd>⌘ K</kbd></div><button className="icon-button" aria-label="Notifications"><Bell size={16} /><i /></button><button className="theme-button" onClick={() => setDark((value) => !value)}>{dark ? <Sun size={16} /> : <Moon size={16} />}{dark ? 'Light' : 'Dark'}</button><span className={`live-pill ${live ? '' : 'is-offline'}`}><i /> {live ? 'Live' : 'Connecting'}</span><span className="currency-pill">INR</span></div></header><section className="next-content"><div className="content-frame">{children}</div></section></main>
  </div>;
}
