'use client';

let csrfToken = '';

export async function getSession() {
  const response = await fetch('/api/session', { credentials: 'include', cache: 'no-store' });
  const body = await response.json();
  csrfToken = body.csrf || '';
  return body;
}

export async function api(path, options = {}) {
  if (!csrfToken && options.method && options.method !== 'GET') await getSession();
  const response = await fetch(`/api${path}`, {
    credentials: 'include',
    cache: 'no-store',
    ...options,
    headers: {
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
      ...(options.method && options.method !== 'GET' ? { 'X-CSRF-Token': csrfToken } : {}),
      ...(options.headers || {}),
    },
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && typeof window !== 'undefined') window.location.href = '/login';
    throw new Error(body.error || 'The request could not be completed.');
  }
  return body;
}

export const send = (path, method, body) => api(path, { method, body: JSON.stringify(body) });
