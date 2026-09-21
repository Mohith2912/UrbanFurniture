'use client';

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { api, getSession } from '@/lib/api';
import WorkspaceLoader from './workspace-loader';

const WorkspaceContext = createContext(null);

export function WorkspaceProvider({ children }) {
  const [user, setUser] = useState(null);
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [live, setLive] = useState(false);

  const refresh = useCallback(async () => {
    try {
      const result = await api('/data');
      setData(result); setError('');
    } catch (err) { setError(err.message); }
  }, []);

  useEffect(() => {
    let stream;
    getSession().then((session) => {
      if (!session.user) { window.location.href = '/login'; return; }
      setUser(session.user);
      return api('/data');
    }).then((result) => {
      if (!result) return;
      setData(result);
      let revision = Number(result.revision || 0);
      stream = new EventSource('/api/events', { withCredentials: true });
      stream.onopen = () => setLive(true);
      stream.onerror = () => setLive(false);
      stream.addEventListener('change', (event) => {
        try { const next = Number(JSON.parse(event.data).revision); if (next > revision) { revision = next; refresh(); } } catch { /* heartbeat */ }
      });
    }).catch((err) => setError(err.message));
    return () => stream?.close();
  }, [refresh]);

  const value = useMemo(() => ({ user, data, error, live, refresh }), [user, data, error, live, refresh]);
  if (error && !data) return <main className="next-error"><div className="error-mark">!</div><small>CONNECTION PAUSED</small><h1>Unable to open workspace</h1><p>{error}</p><button onClick={() => location.reload()}>Try again</button></main>;
  if (!user || !data) return <WorkspaceLoader />;
  return <WorkspaceContext.Provider value={value}>{children}</WorkspaceContext.Provider>;
}

export function useWorkspace() {
  const value = useContext(WorkspaceContext);
  if (!value) throw new Error('useWorkspace must be used inside WorkspaceProvider.');
  return value;
}
