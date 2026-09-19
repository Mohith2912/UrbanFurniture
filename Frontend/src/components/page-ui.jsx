'use client';

import { X } from 'lucide-react';

export function PageIntro({ eyebrow, title, description, action }) {
  return <section className="role-hero"><div><small>{eyebrow}</small><h2>{title}</h2><p>{description}</p></div>{action && <div className="hero-actions">{action}</div>}</section>;
}

export function Panel({ title, eyebrow, meta, children, className = '' }) {
  return <section className={`next-card section-card ${className}`}><div className="card-heading"><div><small>{eyebrow}</small><h3>{title}</h3></div>{meta && <span>{meta}</span>}</div>{children}</section>;
}

export function Empty({ icon: Icon, title, text }) { return <div className="next-empty"><Icon size={22} /><strong>{title}</strong><p>{text}</p></div>; }

export function Modal({ title, children, onClose, wide = false }) {
  return <div className="dialog-backdrop" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && onClose()}><section className={`next-dialog ${wide ? 'wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}><header><h2>{title}</h2><button type="button" onClick={onClose} aria-label="Close"><X size={18} /></button></header><div className="dialog-body">{children}</div></section></div>;
}

export function FormMessage({ error, success }) { return <>{error && <p className="form-message error">{error}</p>}{success && <p className="form-message success">{success}</p>}</>; }

export function Status({ children, tone = 'neutral' }) { return <span className={`status status-${tone}`}>{children}</span>; }
