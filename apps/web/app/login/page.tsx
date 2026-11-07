import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { ownerSession } from '../../lib/owner-access.mjs';
import {locationId, locationLink} from '../../lib/location-link';
import LoginForm from './login-form';

export const dynamic = 'force-dynamic';
export default async function Login({searchParams}: {searchParams: Promise<{location?:string|string[]}>}) {
  const id = locationId((await searchParams).location);
  const session = await ownerSession(await headers());
  if (session.status === 200) redirect(locationLink(id));
  if (session.status !== 401) return <main className="access-shell"><h1>Owner access unavailable</h1><p>Use the configured private address. Owner access must be set up on the server before signing in.</p><a href={id ? `/login?location=${id}` : '/login'}>Try again</a></main>;
  return <main className="access-shell"><a className="brand" href="/">RelicRat</a><h1>Sign in to your collection</h1><p>Use the owner password set up on your private server.</p><LoginForm destination={locationLink(id)} /><p className="hint">Single-owner access. There is no public signup. Contact your server operator if you need to reset access.</p></main>;
}
