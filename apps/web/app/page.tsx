import { headers } from 'next/headers';
import { redirect } from 'next/navigation';
import { ownerSession } from '../lib/owner-access.mjs';
import InventoryClient from './inventory-client';

export const dynamic = 'force-dynamic';
export default async function Home() {
  const session = await ownerSession(await headers());
  if (session.status === 401) redirect('/login');
  if (session.status !== 200) return <main className="access-shell"><h1>Owner access unavailable</h1><p>Open the configured RelicRat address. If it is correct, check the private service and try again.</p><a href="/">Try again</a></main>;
  return <InventoryClient />;
}
