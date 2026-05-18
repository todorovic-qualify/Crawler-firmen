import { ActionType, Category, EmailGroup } from '@/types/email';

const KEYWORDS: Record<Exclude<Category, 'other'>, string[]> = {
  pv_energy: [
    'solar', 'pv', 'photovoltaik', 'wärmepumpe', 'waermepumpe', 'energie',
    'strom', 'einspeise', 'wallbox', 'e-auto', 'heizung', 'wechselrichter',
    'stromspeicher', 'balkonkraftwerk', 'solaranlage', 'klimaanlage',
  ],
  qualify_ai: [
    'qualify', 'künstliche intelligenz', 'automatisierung', 'gpt', 'claude',
    'openai', 'anthropic', 'llm', 'chatbot', 'automation', 'copilot',
    'machine learning', 'deep learning', ' ki ', ' ai ', 'saas', 'crm',
  ],
  finance: [
    'rechnung', 'invoice', 'steuer', 'finanz', 'bank', 'zahlung', 'payment',
    'konto', 'überweisung', 'sepa', 'lastschrift', 'mahnung', 'buchhaltung',
    'elster', 'abrechnung', 'quittung', 'umsatz', 'kontoauszug', 'iban',
    'steuererklärung', 'finanzen', 'lohnsteuer', 'umsatzsteuer',
  ],
  construction: [
    'hausbau', 'immobilie', 'handwerker', 'baustelle', 'architekt', 'grundstück',
    'wohnung', 'miete', 'renovier', 'umbau', 'neubau', 'baugenehmigung',
    'bauantrag', 'maler', 'elektriker', 'sanitär', 'dachdecke', 'fenster',
    'fliesen', 'estrich',
  ],
  newsletter: [
    'newsletter', 'unsubscribe', 'abmelden', 'marketing', 'angebot', 'deal',
    'sale', 'rabatt', 'werbung', 'promotion', 'promo', 'sonderangebot',
    'exklusiv für', 'neuigkeiten von', 'update von', 'jetzt kaufen',
    'jetzt shoppen', 'bestell jetzt',
  ],
  important: [
    'dringend', 'urgent', 'persönlich', 'vertraulich', 'sofort', 'frist',
    'deadline', 'termin', 'wichtige mitteilung',
  ],
};

export function categorize(
  from: string,
  subject: string,
  hasListUnsubscribe: boolean
): Category {
  if (hasListUnsubscribe) return 'newsletter';

  const text = `${from} ${subject}`.toLowerCase();

  for (const [cat, keywords] of Object.entries(KEYWORDS) as [Category, string[]][]) {
    if (keywords.some((kw) => text.includes(kw))) return cat;
  }

  return 'other';
}

export function suggestAction(group: EmailGroup): ActionType {
  if (group.isNewsletter || group.category === 'newsletter') return 'archive';
  if (group.count >= 10) return 'archive';
  if (group.category === 'finance' || group.category === 'important') return 'keep';
  return 'keep';
}
