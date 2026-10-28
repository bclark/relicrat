import { ownerAction } from '../../../../../lib/owner-access.mjs';
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
type Context = { params: Promise<{ action: string }> };
export async function POST(request: Request, context: Context) {
  return ownerAction(request, (await context.params).action);
}
