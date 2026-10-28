import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { ownerSession } from '../../lib/owner-access.mjs';
import LoginForm from './login-form';

export const dynamic = 'force-dynamic';
export default async function Login() {
  const session = await ownerSession(await headers());
  if (session.status === 200) redirect('/');
  if (session.status !== 401) return <main className="access-shell"><h1>Owner access unavailable</h1><p>Use the configured private address. Owner access must be set up on the server before signing in.</p><a href="/login">Try again</a></main>;
  return <main className="access-shell"><a className="brand" href="/">RelicRat</a><h1>Sign in to your collection</h1><p>Use the owner password set up on your private server.</p><LoginForm /><p className="hint">Single-owner access. There is no public signup. Contact your server operator if you need to reset access.</p></main>;
}
