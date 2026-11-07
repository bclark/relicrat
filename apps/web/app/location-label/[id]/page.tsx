import {headers} from 'next/headers';
import {notFound, redirect} from 'next/navigation';
import {ownerSession} from '../../../lib/owner-access.mjs';
import {webConfig} from '../../../lib/server-security.mjs';
import {locationId,locationLink} from '../../../lib/location-link';
import LocationLabel from './location-label';

export const dynamic = 'force-dynamic';

export default async function LabelPage({params}: {params:Promise<{id:string}>}) {
  const id = locationId((await params).id);
  if (!id) notFound();
  const session = await ownerSession(await headers());
  if (session.status === 401) redirect(`/login?location=${id}`);
  if (session.status !== 200) return <main className="access-shell"><h1>Owner access unavailable</h1><a href={locationLink(id)}>Open location</a></main>;
  return <LocationLabel id={id} url={new URL(locationLink(id),webConfig().origin).href} />;
}
