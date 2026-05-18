import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';
import { authOptions } from '@/lib/auth';
import { executeGmailAction } from '@/lib/gmail';
import { ActionType } from '@/types/email';

const VALID_ACTIONS: ActionType[] = ['archive', 'delete', 'markRead', 'markUnread', 'addLabel'];

export async function POST(req: NextRequest) {
  const session = await getServerSession(authOptions);

  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Nicht angemeldet' }, { status: 401 });
  }

  const body = await req.json();
  const { action, ids, label } = body as {
    action: ActionType;
    ids: string[];
    label?: string;
  };

  if (!VALID_ACTIONS.includes(action)) {
    return NextResponse.json({ error: 'Ungültige Aktion' }, { status: 400 });
  }
  if (!ids || ids.length === 0) {
    return NextResponse.json({ error: 'Keine E-Mail-IDs angegeben' }, { status: 400 });
  }
  if (action === 'addLabel' && !label) {
    return NextResponse.json({ error: 'Label-Name fehlt' }, { status: 400 });
  }

  try {
    await executeGmailAction(session.accessToken, action, ids, label);
    return NextResponse.json({ success: true, count: ids.length });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : String(err);
    console.error('[actions]', msg);
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
