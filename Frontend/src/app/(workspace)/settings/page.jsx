'use client';

import { useState } from 'react';
import { Download, LockKeyhole, Save, ShieldCheck } from 'lucide-react';
import { send } from '@/lib/api';
import { FormMessage, PageIntro, Panel, Status } from '@/components/page-ui';
import { useWorkspace } from '@/components/workspace-provider';

export default function SettingsPage() {
  const { user, data, refresh } = useWorkspace();
  const [profileMessage, setProfileMessage] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [error, setError] = useState('');
  async function saveProfile(event) { event.preventDefault(); setError(''); try { await send('/workspace', 'PATCH', Object.fromEntries(new FormData(event.currentTarget))); await refresh(); setProfileMessage('Company profile saved.'); } catch (err) { setError(err.message); } }
  async function password(event) { event.preventDefault(); setError(''); try { await send('/password', 'POST', Object.fromEntries(new FormData(event.currentTarget))); event.currentTarget.reset(); setPasswordMessage('Password changed.'); } catch (err) { setError(err.message); } }
  return <><PageIntro eyebrow="COMPANY AND ACCESS" title="Settings" description="Manage company invoice details, your password, user access and private backups." /><FormMessage error={error} />
    <section className="section-grid">{user.role === 'admin' && <Panel eyebrow="BUSINESS IDENTITY" title="Company and invoice profile"><form className="settings-form" onSubmit={saveProfile}><label>Company name<input name="company_name" defaultValue={data.workspace?.company_name} required /></label><label>Email<input name="email" type="email" defaultValue={data.workspace?.email} /></label><label>Phone<input name="phone" defaultValue={data.workspace?.phone} /></label><label>Address<textarea name="address" defaultValue={data.workspace?.address} rows={3} /></label><label>State<input name="state" defaultValue={data.workspace?.state} /></label><label>State code<input name="state_code" maxLength={2} defaultValue={data.workspace?.state_code} /></label><label>GSTIN<input name="tax_id" maxLength={15} defaultValue={data.workspace?.tax_id} /></label><label>Default payment days<input name="default_terms" type="number" min="0" max="365" defaultValue={data.workspace?.default_terms || 30} /></label><label>Bank name<input name="bank_name" defaultValue={data.workspace?.bank_name} /></label><label>Account number<input name="account_number" defaultValue={data.workspace?.account_number} /></label><label>IFSC<input name="ifsc" defaultValue={data.workspace?.ifsc} /></label><label>Invoice notes<textarea name="invoice_note" defaultValue={data.workspace?.invoice_note} rows={3} /></label><FormMessage success={profileMessage} /><button className="next-primary compact"><Save size={15} /> Save profile</button></form></Panel>}
      <Panel eyebrow="YOUR ACCOUNT" title="Security"><div className="account-summary"><span>{user.name?.slice(0, 2).toUpperCase()}</span><div><strong>{user.name}</strong><p>{user.email}</p><Status tone="green">{user.role}</Status></div></div><form className="settings-form password-settings" onSubmit={password}><label>Current password<input name="current" type="password" autoComplete="current-password" required /></label><label>New password<input name="password" type="password" minLength={10} autoComplete="new-password" required /></label><FormMessage success={passwordMessage} /><button className="next-primary compact"><LockKeyhole size={15} /> Change password</button></form>{user.role === 'admin' && <a className="soft-link backup-link" href="/api/backup"><Download size={15} /> Download private backup</a>}</Panel>
    </section>
    {user.role === 'admin' && <Panel eyebrow="PEOPLE AND ACCESS" title="Workspace users" meta={`${data.users?.length || 0} accounts`}><div className="section-table">{(data.users || []).map((person) => <div className="section-row" key={person.id}><span><b>{person.name}</b><small>{person.email}</small></span><span><ShieldCheck size={15} /><Status tone={person.active ? 'green' : 'red'}>{person.active ? person.role : 'disabled'}</Status></span></div>)}</div></Panel>}
  </>;
}
