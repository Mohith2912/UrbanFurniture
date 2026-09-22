'use client';

let csrfToken = '';

async function jsonBody(response) {
  const text = await response.text();
  if (!text) return {};
  try { return JSON.parse(text); }
  catch {
    throw new Error(response.ok
      ? 'The server returned an unexpected response.'
      : 'The accounting service is temporarily unavailable. Please try again shortly.');
  }
}

export async function getSession() {
  const response = await fetch('/api/session', { credentials: 'include', cache: 'no-store' });
  const body = await jsonBody(response);
  if (!response.ok) throw new Error(body.error || 'The accounting service is temporarily unavailable.');
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
  const body = await jsonBody(response);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== 'undefined') window.location.href = '/login';
    throw new Error(body.error || 'The request could not be completed.');
  }
  return body;
}

export const send = (path, method, body) => api(path, { method, body: JSON.stringify(body) });
