'use client';

import { useState } from 'react';
import { Printer, WalletCards } from 'lucide-react';
import { send } from '@/lib/api';
import { dateText, money, today } from '@/lib/format';
import { FormMessage } from './page-ui';
import { useWorkspace } from './workspace-provider';

function words(value) {
  const ones = ['', 'One', 'Two', 'Three', 'Four', 'Five', 'Six', 'Seven', 'Eight', 'Nine', 'Ten', 'Eleven', 'Twelve', 'Thirteen', 'Fourteen', 'Fifteen', 'Sixteen', 'Seventeen', 'Eighteen', 'Nineteen'];
  const tens = ['', '', 'Twenty', 'Thirty', 'Forty', 'Fifty', 'Sixty', 'Seventy', 'Eighty', 'Ninety'];
  const convert = (n) => { if (n < 20) return ones[n]; if (n < 100) return `${tens[Math.floor(n / 10)]}${n % 10 ? ` ${ones[n % 10]}` : ''}`; for (const [div, label] of [[10000000, 'Crore'], [100000, 'Lakh'], [1000, 'Thousand'], [100, 'Hundred']]) if (n >= div) return `${convert(Math.floor(n / div))} ${label}${n % div ? ` ${convert(n % div)}` : ''}`; return ''; };
  const amount = Math.max(0, Math.round(Number(value || 0)));
  return `${convert(Math.floor(amount / 100)) || 'Zero'} Rupees${amount % 100 ? ` and ${convert(amount % 100)} Paise` : ''} Only`;
}

export default function InvoiceView({ detail, onUpdated }) {
  const { user } = useWorkspace();
  const { document: doc, order, contact, seller, lines = [], payments = [] } = detail;
  const [paying, setPaying] = useState(false);
  const [error, setError] = useState('');
  const balance = Number(doc.total) - Number(doc.paid);
  const taxLabel = order.tax_mode === 'inter' ? 'IGST' : order.tax_mode === 'exempt' ? 'Exempt' : 'CGST and SGST';
  async function pay(event) {
    event.preventDefault(); setError('');
    const values = Object.fromEntries(new FormData(event.currentTarget));
    try {
      if (user.role === 'contact') await send('/payment-requests', 'POST', { ...values, document_id: doc.id });
      else await send(`/documents/${doc.id}/payments`, 'POST', values);
      setPaying(false); await onUpdated();
    } catch (err) { setError(err.message); }
  }
  return <><article className="invoice-sheet" id="print-invoice"><header className="invoice-top"><div><div className="invoice-logo"><span>UF</span><strong>{seller.company_name}</strong></div><p>{seller.address || 'Company address not configured'}</p><p>{[seller.state, seller.state_code && `State code ${seller.state_code}`].filter(Boolean).join(' · ')}</p><p>{[seller.email, seller.phone].filter(Boolean).join(' · ')}</p>{seller.tax_id && <b>GSTIN {seller.tax_id}</b>}</div><div className="invoice-number"><small>{doc.kind === 'sale' ? 'TAX INVOICE' : 'VENDOR BILL'}</small><h2>{doc.number}</h2><span>{balance <= 0 ? 'PAID' : new Date(doc.due_date) < new Date(today()) ? 'OVERDUE' : 'PAYMENT DUE'}</span></div></header>
    <section className="invoice-meta"><div><small>ISSUE DATE</small><strong>{dateText(doc.date)}</strong></div><div><small>DUE DATE</small><strong>{dateText(doc.due_date)}</strong></div><div><small>ORDER</small><strong>{order.number}</strong></div><div><small>PLACE OF SUPPLY</small><strong>{order.place_of_supply || 'Not specified'}</strong></div></section>
    <section className="invoice-parties-next"><div><small>{doc.kind === 'sale' ? 'BILL TO' : 'SUPPLIER'}</small><h3>{contact.name}</h3><p>{contact.address}</p><p>{[contact.city, contact.state, contact.pincode].filter(Boolean).join(', ')}</p><p>{[contact.email, contact.mobile].filter(Boolean).join(' · ')}</p><b>{contact.gstin ? `GSTIN ${contact.gstin}` : 'GSTIN not supplied'}</b></div><div><small>SUPPLY AND PAYMENT</small><p>Tax treatment <b>{taxLabel}</b></p><p>Currency <b>INR</b></p><p>Balance due <b>{money(balance)}</b></p></div></section>
    <div className="invoice-table-wrap"><table><thead><tr><th>#</th><th>Item</th><th>HSN/SAC</th><th>Qty</th><th>Rate</th><th>Taxable</th><th>GST</th><th>Amount</th></tr></thead><tbody>{lines.map((line, index) => <tr key={line.id}><td>{index + 1}</td><td><b>{line.description}</b></td><td>{line.hsn || '—'}</td><td>{line.quantity} {line.unit}</td><td>{money(line.unit_price)}</td><td>{money(line.subtotal)}</td><td>{line.tax_rate}%<small>{money(line.tax)}</small></td><td><b>{money(line.total)}</b></td></tr>)}</tbody></table></div>
    <section className="invoice-summary"><div><small>AMOUNT IN WORDS</small><p>{words(doc.total)}</p><small>PAYMENT DETAILS</small><p>{seller.bank_name || 'Contact the company for payment instructions.'}{seller.account_number ? ` · Account ${seller.account_number}` : ''}{seller.ifsc ? ` · IFSC ${seller.ifsc}` : ''}</p></div><div><p><span>Taxable amount</span><b>{money(order.subtotal)}</b></p>{order.tax_mode === 'intra' && <><p><span>CGST</span><b>{money(order.cgst)}</b></p><p><span>SGST</span><b>{money(order.sgst)}</b></p></>}{order.tax_mode === 'inter' && <p><span>IGST</span><b>{money(order.igst)}</b></p>}<p className="grand"><span>Grand total</span><b>{money(doc.total)}</b></p><p><span>Received</span><b>{money(doc.paid)}</b></p><p className="balance"><span>Balance due</span><b>{money(balance)}</b></p></div></section>
    <section className="invoice-notes-next"><div><small>TERMS AND NOTES</small><p>{seller.invoice_note || 'Payment is due by the date shown above.'}</p>{order.notes && <p>{order.notes}</p>}</div><div><p>For {seller.company_name}</p><span>Authorized signatory</span></div></section><footer><span>{seller.company_name}</span><span>Computer-generated invoice · {doc.number}</span></footer></article>
    <div className="invoice-actions no-print"><button className="soft-link" onClick={() => window.print()}><Printer size={15} /> Print or save PDF</button>{balance > 0 && <button className="next-primary compact" onClick={() => setPaying((v) => !v)}><WalletCards size={15} /> {user.role === 'contact' ? 'Submit payment' : 'Record payment'}</button>}</div>
    {paying && <form className="payment-form no-print" onSubmit={pay}><label>Amount<input name="amount" type="number" min="0.01" max={(balance / 100).toFixed(2)} step="0.01" defaultValue={(balance / 100).toFixed(2)} required /></label><label>Date<input name="date" type="date" min={doc.date} defaultValue={today()} required /></label><label>Method<select name="method"><option>Bank</option><option>Cash</option></select></label><label>Reference<input name="reference" required={user.role === 'contact'} /></label><FormMessage error={error} /><button className="next-primary compact" type="submit">Save payment</button></form>}
    {payments.length > 0 && <section className="payment-history no-print"><h3>Payment history</h3>{payments.map((payment) => <div className="section-row" key={payment.id}><span><b>{payment.number}</b><small>{dateText(payment.date)} · {payment.method}</small></span><strong>{money(payment.amount)}</strong></div>)}</section>}
  </>;
}
