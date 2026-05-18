import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { fetchEmails, groupEmails, computeStats } from '@/lib/gmail';

export async function GET(req: NextRequest) {
  const session = await getServerSession(authOptions);

  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Nicht angemeldet' }, { status: 401 });
  }
  if (session.error === 'RefreshAccessTokenError') {
    return NextResponse.json({ error: 'Sitzung abgelaufen — bitte neu anmelden' }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const limit = Math.min(parseInt(searchParams.get('limit') ?? '300', 10), 1000);

  try {
    const emails = await fetchEmails(session.accessToken, limit);
    const groups = groupEmails(emails);
    const stats = computeStats(emails);
    return NextResponse.json({ groups, stats, total: emails.length });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('[analyze]', msg);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
