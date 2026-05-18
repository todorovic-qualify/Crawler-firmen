import { google, gmail_v1 } from 'googleapis';
import { ActionType, Category, DashboardStats, EmailGroup, EmailMeta } from '@/types/email';
import { categorize, suggestAction } from './categorize';

function createClient(accessToken: string) {
  const auth = new google.auth.OAuth2(
    process.env.GOOGLE_CLIENT_ID,
    process.env.GOOGLE_CLIENT_SECRET
  );
  auth.setCredentials({ access_token: accessToken });
  return google.gmail({ version: 'v1', auth });
}

function parseHeaders(headers: gmail_v1.Schema$MessagePartHeader[]): Record<string, string> {
  return Object.fromEntries((headers || []).map((h) => [h.name ?? '', h.value ?? '']));
}

function parseSender(from: string): { name: string; email: string } {
  const m = from.match(/^"?([^"<]+?)"?\s*<([^>]+)>/);
  if (m) return { name: m[1].trim(), email: m[2].trim().toLowerCase() };
  if (from.includes('@')) return { name: from.split('@')[0], email: from.toLowerCase() };
  return { name: from, email: '' };
}

export async function fetchEmails(accessToken: string, maxResults = 300): Promise<EmailMeta[]> {
  const gmail = createClient(accessToken);
  const msgIds: { id: string; threadId: string }[] = [];
  let pageToken: string | undefined;

  while (msgIds.length < maxResults) {
    const res = await gmail.users.messages.list({
      userId: 'me',
      maxResults: Math.min(100, maxResults - msgIds.length),
      labelIds: ['INBOX'],
      pageToken,
    });
    const msgs = (res.data.messages ?? []) as { id: string; threadId: string }[];
    msgIds.push(...msgs);
    pageToken = res.data.nextPageToken ?? undefined;
    if (!pageToken || msgs.length === 0) break;
  }

  const BATCH = 25;
  const emails: EmailMeta[] = [];

  for (let i = 0; i < msgIds.length; i += BATCH) {
    const slice = msgIds.slice(i, i + BATCH);
    const results = await Promise.allSettled(
      slice.map((m) =>
        gmail.users.messages.get({
          userId: 'me',
          id: m.id,
          format: 'metadata',
          metadataHeaders: ['From', 'Subject', 'Date', 'List-Unsubscribe'],
        })
      )
    );

    for (const r of results) {
      if (r.status !== 'fulfilled') continue;
      const msg = r.value.data;
      const h = parseHeaders(msg.payload?.headers ?? []);
      const from = h['From'] ?? 'Unbekannt';
      const { name, email } = parseSender(from);
      const subject = h['Subject'] ?? '(kein Betreff)';
      const hasUnsub = !!h['List-Unsubscribe'];
      const isRead = !(msg.labelIds ?? []).includes('UNREAD');
      const cat = categorize(from, subject, hasUnsub);

      emails.push({
        id: msg.id!,
        threadId: msg.threadId!,
        from, fromName: name, fromEmail: email, subject,
        date: h['Date'] ?? '',
        snippet: msg.snippet ?? '',
        isRead, isNewsletter: hasUnsub, category: cat,
        labels: msg.labelIds ?? [],
      });
    }
  }

  return emails;
}

export function groupEmails(emails: EmailMeta[]): EmailGroup[] {
  const map = new Map<string, EmailGroup>();

  for (const e of emails) {
    const key = e.fromEmail || e.fromName.toLowerCase();
    if (!map.has(key)) {
      map.set(key, {
        sender: e.from, senderName: e.fromName, senderEmail: e.fromEmail,
        count: 0, unreadCount: 0, category: e.category, isNewsletter: e.isNewsletter,
        subjects: [], ids: [], threadIds: [], latestDate: e.date, suggestedAction: 'keep',
      });
    }
    const g = map.get(key)!;
    g.count++;
    if (!e.isRead) g.unreadCount++;
    if (!g.subjects.includes(e.subject)) g.subjects.push(e.subject);
    g.ids.push(e.id);
    if (!g.threadIds.includes(e.threadId)) g.threadIds.push(e.threadId);
    if (e.isNewsletter) g.isNewsletter = true;
    if (e.category !== 'other') g.category = e.category;
  }

  return Array.from(map.values())
    .map((g) => ({ ...g, suggestedAction: suggestAction(g) }))
    .sort((a, b) => b.count - a.count);
}

export function computeStats(emails: EmailMeta[]): DashboardStats {
  const breakdown: Record<Category, number> = {
    pv_energy: 0, qualify_ai: 0, finance: 0, construction: 0,
    newsletter: 0, important: 0, other: 0,
  };
  let totalUnread = 0, newsletterCount = 0, financeCount = 0;

  for (const e of emails) {
    breakdown[e.category]++;
    if (!e.isRead) totalUnread++;
    if (e.isNewsletter || e.category === 'newsletter') newsletterCount++;
    if (e.category === 'finance') financeCount++;
  }

  const senderCounts = new Map<string, number>();
  for (const e of emails) {
    const k = e.fromEmail || e.fromName;
    senderCounts.set(k, (senderCounts.get(k) ?? 0) + 1);
  }
  const duplicateGroups = Array.from(senderCounts.values()).filter((c) => c >= 3).length;

  return {
    totalEmails: emails.length, totalUnread, newsletterCount, financeCount, duplicateGroups,
    businessCount: breakdown.qualify_ai + breakdown.pv_energy,
    categoryBreakdown: breakdown,
  };
}

export async function executeGmailAction(
  accessToken: string, action: ActionType, ids: string[], label?: string
): Promise<void> {
  const gmail = createClient(accessToken);
  const CHUNK = 1000;

  for (let i = 0; i < ids.length; i += CHUNK) {
    const chunk = ids.slice(i, i + CHUNK);
    switch (action) {
      case 'archive':
        await gmail.users.messages.batchModify({ userId: 'me', requestBody: { ids: chunk, removeLabelIds: ['INBOX'] } }); break;
      case 'delete':
        await gmail.users.messages.batchModify({ userId: 'me', requestBody: { ids: chunk, addLabelIds: ['TRASH'], removeLabelIds: ['INBOX'] } }); break;
      case 'markRead':
        await gmail.users.messages.batchModify({ userId: 'me', requestBody: { ids: chunk, removeLabelIds: ['UNREAD'] } }); break;
      case 'markUnread':
        await gmail.users.messages.batchModify({ userId: 'me', requestBody: { ids: chunk, addLabelIds: ['UNREAD'] } }); break;
      case 'addLabel': {
        if (!label) break;
        const labelId = await getOrCreateLabel(gmail, label);
        await gmail.users.messages.batchModify({ userId: 'me', requestBody: { ids: chunk, addLabelIds: [labelId] } }); break;
      }
    }
  }
}

async function getOrCreateLabel(gmail: gmail_v1.Gmail, name: string): Promise<string> {
  const res = await gmail.users.labels.list({ userId: 'me' });
  const existing = (res.data.labels ?? []).find((l) => l.name === name);
  if (existing?.id) return existing.id;
  const created = await gmail.users.labels.create({
    userId: 'me',
    requestBody: { name, labelListVisibility: 'labelShow', messageListVisibility: 'show' },
  });
  return created.data.id!;
}
