'use client';
import { useRef, useState, type FormEvent } from 'react';
export default function LoginForm() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const pending = useRef(false);
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (pending.current) return;
    const form = event.currentTarget;
    const password = new FormData(form).get('password');
    if (typeof password !== 'string' || !password) return;
    pending.current = true; setBusy(true); setError('');
    try {
      const response = await fetch('/api/v1/auth/login', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ password }), signal: AbortSignal.timeout(20_000), cache: 'no-store' });
      const body = await response.json();
      if (!response.ok || body.authenticated !== true) throw new Error(typeof body.detail === 'string' ? body.detail : 'Sign in could not be confirmed. Try again');
      form.reset(); window.location.replace('/');
    } catch (problem) { setError(problem instanceof Error && problem.name !== 'TimeoutError' ? problem.message : 'Sign in could not be confirmed. Try again'); }
    finally { pending.current = false; setBusy(false); }
  }
  return <form method="post" onSubmit={submit} aria-label="Owner sign in">{error && <p className="error" role="alert">{error}</p>}<fieldset disabled={busy}><label htmlFor="owner-password">Owner password</label><input id="owner-password" type="password" name="password" autoComplete="current-password" required maxLength={256} /><button type="submit">{busy ? 'Signing in…' : 'Sign in'}</button></fieldset><p role="status" className="hint">{busy ? 'Checking owner access…' : ''}</p></form>;
}
