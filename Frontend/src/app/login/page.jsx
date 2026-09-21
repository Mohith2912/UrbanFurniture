'use client';

import { useEffect, useState } from 'react';
import { ArrowRight, Eye, EyeOff, Layers3, Moon, Radio, ShieldCheck, Sparkles, Sun } from 'lucide-react';
import Brand from '@/components/brand';

export default function Login() {
  const [error, setError] = useState('');
  const [dark, setDark] = useState(false);
  const [loading, setLoading] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const demoAccounts = [
    { role: 'Administrator', email: 'jmohith@gmail.com', password: 'Mohith@2912', destination: '/dashboard', initials: 'AD' },
    { role: 'Accountant', email: 'jmohith2912@gmail.com', password: 'Accounts@2912', destination: '/accounting', initials: 'AC' },
    { role: 'Customer portal', email: 'demo.customer@urbanfurniture.in', password: 'Customer@2912', destination: '/documents', initials: 'CU' },
  ];
  useEffect(() => {
    const saved = localStorage.getItem('urban-theme') === 'dark';
    setDark(saved); document.documentElement.dataset.theme = saved ? 'dark' : 'light';
  }, []);
  function toggleTheme() {
    const next = !dark; setDark(next); document.documentElement.dataset.theme = next ? 'dark' : 'light'; localStorage.setItem('urban-theme', next ? 'dark' : 'light');
  }
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
  return <main className="next-login">
    <section className="login-panel">
      <span className="login-aurora login-aurora-one" /><span className="login-aurora login-aurora-two" />
      <Brand inverse />
      <div className="login-copy"><small><Sparkles size={12} /> THE BUSINESS OS FOR FURNITURE</small><h1>Craft the business<br /><em>behind the furniture.</em></h1><p>Bring sales, inventory, GST invoices and finances into one beautifully focused workspace.</p>
        <div className="login-proof"><span><ShieldCheck size={16} /><b>Role-secure</b><small>Access by responsibility</small></span><span><Radio size={16} /><b>Live data</b><small>Synced in real time</small></span><span><Layers3 size={16} /><b>One system</b><small>Orders through reports</small></span></div>
      </div>
      <div className="login-foot"><span className="login-live"><i /> System online</span><span>GST-ready · PostgreSQL powered</span></div>
    </section>
    <section className="login-form"><button className="floating-theme" onClick={toggleTheme} aria-label="Toggle theme">{dark ? <Sun size={17} /> : <Moon size={17} />}<span>{dark ? 'Light' : 'Dark'}</span></button><div className="login-form-inner"><div className="login-heading"><small>SECURE SIGN IN</small><h2>Welcome back.</h2><p>Continue to your Urban Furniture workspace.</p></div><form onSubmit={submit}><label>Email address<input name="email" type="email" autoComplete="username" placeholder="name@urbanfurniture.in" required /></label><label>Password<span className="password-control"><input name="password" type={showPassword ? 'text' : 'password'} autoComplete="current-password" placeholder="Enter your password" required /><button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? 'Hide password' : 'Show password'}>{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></span></label>{error && <div className="next-form-error">{error}</div>}<button className="next-primary login-submit" type="submit" disabled={Boolean(loading)}>{loading ? <><span className="button-spinner" /> Signing in…</> : <>Sign in securely <ArrowRight size={16} /></>}</button></form><div className="demo-login-list"><div className="demo-heading"><span>QUICK DEMO ACCESS</span><small>Choose a workspace</small></div>{demoAccounts.map((account) => <button key={account.email} type="button" onClick={() => signIn(account.email, account.password, account.destination)} disabled={Boolean(loading)}><span>{account.initials}</span><div><strong>{loading === account.email ? 'Opening workspace…' : account.role}</strong><small>{account.email}</small></div><ArrowRight size={15} /></button>)}</div><p className="login-privacy"><ShieldCheck size={13} /> Protected session · Credentials are encrypted in transit</p></div></section>
  </main>;
}
