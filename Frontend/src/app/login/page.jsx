'use client';

import { useState } from 'react';
import { ArrowRight, Moon, Sun } from 'lucide-react';

export default function Login() {
  const [error, setError] = useState('');
  const [dark, setDark] = useState(false);
  async function submit(event) {
    event.preventDefault(); setError('');
    const form = new FormData(event.currentTarget);
    const session = await fetch('/api/session').then((r) => r.json());
    const result = await fetch('/api/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': session.csrf }, credentials: 'include', body: JSON.stringify({ email: form.get('email'), password: form.get('password') }) });
    if (!result.ok) { const body = await result.json().catch(() => ({})); setError(body.error || 'Unable to sign in.'); return; }
    window.location.href = '/dashboard';
  }
  return <main className="next-login"><section className="login-panel"><div className="next-brand"><span>UF</span><div>Urban Furniture<small>BOOKS & BUSINESS</small></div></div><div className="login-copy"><small>PEOPLEPAY360-INSPIRED WORKSPACE</small><h1>Beautiful furniture.<br />Balanced books.</h1><p>Sales, purchases and finances brought together in a focused role-aware workspace.</p></div><small className="login-foot">Live PostgreSQL accounting workspace</small></section><section className="login-form"><button className="floating-theme" onClick={() => { setDark(!dark); document.documentElement.dataset.theme = !dark ? 'dark' : 'light'; }} aria-label="Toggle theme">{dark ? <Sun size={17} /> : <Moon size={17} />}</button><div className="login-form-inner"><small>WELCOME BACK</small><h2>Good to see you.</h2><p>Sign in to your Urban Furniture workspace.</p><form onSubmit={submit}><label>Email address<input name="email" type="email" autoComplete="username" required /></label><label>Password<input name="password" type="password" autoComplete="current-password" required /></label>{error && <div className="next-form-error">{error}</div>}<button className="next-primary" type="submit">Sign in <ArrowRight size={16} /></button></form></div></section></main>;
}
