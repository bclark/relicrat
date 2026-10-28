'use client';
import { useEffect, useRef, useState } from 'react';
export default function SignOut() {
  const pending = useRef(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  useEffect(() => {
    const refresh = (event: PageTransitionEvent) => { if (event.persisted) window.location.reload(); };
    window.addEventListener('pageshow', refresh);
    return () => window.removeEventListener('pageshow', refresh);
  }, []);
  async function signOut() {
    if (pending.current) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const response = await fetch('/api/v1/auth/logout', { method: 'POST', cache: 'no-store', signal: AbortSignal.timeout(20_000) });
      if (!response.ok) throw new Error();
      window.location.replace('/login');
    } catch { setError('Sign out could not be confirmed. Try again.'); pending.current = false; setBusy(false); }
  }
  return <div className="owner-controls"><button type="button" className="quiet" disabled={busy} onClick={signOut}>{busy ? 'Signing out…' : 'Sign out'}</button>{error && <p className="error" role="alert">{error}</p>}</div>;
}
