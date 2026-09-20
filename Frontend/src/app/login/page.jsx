'use client';

import { useState } from 'react';
import { ArrowRight, Moon, Sun } from 'lucide-react';

export default function Login() {
  const [error, setError] = useState('');
  const [dark, setDark] = useState(false);
  const [loading, setLoading] = useState('');
  const demoAccounts = [
    { role: 'Administrator', email: 'jmohith@gmail.com', password: 'Mohith@2912', destination: '/dashboard', initials: 'AD' },
    { role: 'Accountant', email: 'jmohith2912@gmail.com', password: 'Accounts@2912', destination: '/accounting', initials: 'AC' },
    { role: 'Customer portal', email: 'demo.customer@urbanfurniture.in', password: 'Customer@2912', destination: '/documents', initials: 'CU' },
  ];
  async function signIn(email, password, destination = '/dashboard') {
    setError(''); setLoading(email);
    try {
      const session = await fetch('/api/session', { credentials: 'include' }).then((r) => r.json());
      const result = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf }, credentials: 'include', body: JSON.stringify({ email, password }) });
      if (!result.ok) { const body = await result.json().catch(() => ({})); throw new Error(body.error || 'Unable to sign in.'); }
      window.location.href = destination;
    } catch (err) { setError(err.message); setLoading(''); }
  }
  async function submit(event) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await signIn(form.get('email'), form.get('password'));
  }
  return <main className="next-login"><section className="login-panel"><div className="next-brand"><span>UF</span><div>Urban Furniture<small>BOOKS & BUSINESS</small></div></div><div className="login-copy"><small>ROLE-READY BUSINESS WORKSPACE</small><h1>Beautiful furniture.<br />Balanced books.</h1><p>Sales, purchases and finances brought together in a focused role-aware workspace.</p><div className="demo-login-list"><small>QUICK DEMO ACCESS</small>{demoAccounts.map((account) => <button key={account.email} type="button" onClick={() => signIn(account.email, account.password, account.destination)} disabled={Boolean(loading)}><span>{account.initials}</span><div><strong>{loading === account.email ? 'Opening workspace…' : account.role}</strong><small>{account.email}</small><small>{account.password}</small></div><ArrowRight size={15} /></button>)}</div></div><small className="login-foot">Live PostgreSQL accounting workspace</small></section><section className="login-form"><button className="floating-theme" onClick={() => { setDark(!dark); document.documentElement.dataset.theme = !dark ? 'dark' : 'light'; }} aria-label="Toggle theme">{dark ? <Sun size={17} /> : <Moon size={17} />}</button><div className="login-form-inner"><small>WELCOME BACK</small><h2>Good to see you.</h2><p>Sign in manually or choose a demo account.</p><form onSubmit={submit}><label>Email address<input name="email" type="email" autoComplete="username" required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <div className="next-form-error">{error}</div>}<button className="next-primary" type="submit" disabled={Boolean(loading)}>{loading ? 'Signing in…' : 'Sign in'} <ArrowRight size={16} /></button></form></div></section></main>;
}
