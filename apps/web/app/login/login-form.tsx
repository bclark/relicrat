'use client';
import { useRef, useState, type FormEvent } from 'react';
export default function LoginForm() {
  const [password, setPassword] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(false);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (pending.current || !password) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const response = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }), signal: AbortSignal.timeout(20_000), cache: 'no-store' });
      const body = await response.json();
      if (!response.ok || body.authenticated !== true) throw new Error(typeof body.detail === 'string' ? body.detail : 'Sign in could not be confirmed. Try again');
      setPassword(''); window.location.replace('/');
    } catch (problem) { setError(problem instanceof Error && problem.name !== 'TimeoutError' ? problem.message : 'Sign in could not be confirmed. Try again'); }
    finally { pending.current = false; setBusy(false); }
  }
  return <form onSubmit={submit} aria-label="Owner sign in">{error && <p className="error" role="alert">{error}</p>}<fieldset disabled={busy}><label htmlFor="owner-password">Owner password</label><input id="owner-password" type="password" autoComplete="current-password" required maxLength={256} value={password} onChange={event => setPassword(event.target.value)} /><button type="submit" disabled={!password}>{busy ? 'Signing in…' : 'Sign in'}</button></fieldset><p role="status" className="hint">{busy ? 'Checking owner access…' : ''}</p></form>;
}
