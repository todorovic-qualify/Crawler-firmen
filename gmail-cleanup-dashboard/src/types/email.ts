export type Category =
  | 'pv_energy'
  | 'qualify_ai'
  | 'finance'
  | 'construction'
  | 'newsletter'
  | 'important'
  | 'other';

export type ActionType =
  | 'archive'
  | 'delete'
  | 'markRead'
  | 'markUnread'
  | 'addLabel'
  | 'keep';

export interface EmailMeta {
  id: string;
  threadId: string;
  from: string;
  fromName: string;
  fromEmail: string;
  subject: string;
  date: string;
  snippet: string;
  isRead: boolean;
  isNewsletter: boolean;
  category: Category;
  labels: string[];
}

export interface EmailGroup {
  sender: string;
  senderName: string;
  senderEmail: string;
  count: number;
  unreadCount: number;
  category: Category;
  isNewsletter: boolean;
  subjects: string[];
  ids: string[];
  threadIds: string[];
  latestDate: string;
  suggestedAction: ActionType;
}

export interface DashboardStats {
  totalEmails: number;
  totalUnread: number;
  newsletterCount: number;
  financeCount: number;
  duplicateGroups: number;
  businessCount: number;
  categoryBreakdown: Record<Category, number>;
}

export interface PendingAction {
  action: ActionType;
  ids: string[];
  label?: string;
  senderSummary: string;
  count: number;
  category: Category;
}

export const CATEGORY_LABELS: Record<Category, string> = {
  pv_energy: 'PV & Energie',
  qualify_ai: 'Qualify / KI',
  finance: 'Rechnungen & Finanzen',
  construction: 'Hausbau & Immobilie',
  newsletter: 'Newsletter & Werbung',
  important: 'Wichtig / Persönlich',
  other: 'Sonstiges',
};

export const ACTION_LABELS: Record<ActionType, string> = {
  archive: 'Archivieren',
  delete: 'In Papierkorb',
  markRead: 'Als gelesen markieren',
  markUnread: 'Als ungelesen markieren',
  addLabel: 'Label hinzufügen',
  keep: 'Behalten',
};

export const GMAIL_LABELS = [
  'PV & Energie',
  'Qualify.ai',
  'Rechnungen',
  'Steuer',
  'Hausbau',
  'Kunden',
  'Newsletter',
  'Wichtig prüfen',
] as const;
