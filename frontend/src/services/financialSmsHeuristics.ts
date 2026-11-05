import type { BankAccount, CreditCardAccount } from './accountingService'

type ImportedDraftHint = {
  card_last4?: string | null
  description?: string | null
  source_text?: string | null
}

type CashSource = BankAccount & { sourceKind: 'bank' | 'wallet' }

const normalizedText = (value: string) => value
  .normalize('NFKC')
  .toLocaleLowerCase()
  .replace(/[\u064B-\u065F\u0670]/g, '')
  .replace(/ـ/g, '')

function lastFour(value: string | null | undefined) {
  const digits = (value ?? '').replace(/\D/g, '')
  return digits.length >= 4 ? digits.slice(-4) : null
}

function hasNamedSource(text: string, name: string) {
  const normalizedName = normalizedText(name).trim()
  if (normalizedName.length < 3) return false
  if (/^[a-z0-9 ]+$/i.test(normalizedName)) {
    const escaped = normalizedName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&').replace(/\s+/g, '\\s+')
    return new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}($|[^\\p{L}\\p{N}])`, 'iu').test(text)
  }
  return text.includes(normalizedName)
}

function unique<T>(items: T[]) {
  return items.length === 1 ? items[0] : undefined
}

/** Suggest the source account from the SMS sender, masked account/card suffix, and payment wording. */
export function matchImportedPaymentSource(
  draft: ImportedDraftHint,
  bankAccounts: BankAccount[],
  digitalWallets: BankAccount[],
  creditCards: CreditCardAccount[],
): string | null {
  const text = normalizedText(`${draft.source_text ?? ''} ${draft.description ?? ''}`)
  const cashSources: CashSource[] = [
    ...digitalWallets.map((item) => ({ ...item, sourceKind: 'wallet' as const })),
    ...bankAccounts.map((item) => ({ ...item, sourceKind: 'bank' as const })),
  ]

  const namedWallet = unique(digitalWallets.filter((item) =>
    hasNamedSource(text, item.account_name) || hasNamedSource(text, item.bank_name),
  ))
  if (namedWallet) return String(namedWallet.id)

  const debitOrAccountHint = /\b(?:mada|debit)\b|مدى|خصم مباشر|(?:bank\s+)?account\s*[*x•]|حساب\s*[*x•]/iu.test(text)
  const creditCardHint = /credit\s*card|بطاقة\s*(?:ائتمان|ائتمانية)|(?:card|بطاقة)\s*(?:ending|تنتهي)|\bvisa\b|\bmastercard\b/iu.test(text)
  const cardSuffix = lastFour(draft.card_last4)
  const accountSuffixMatch = text.match(/(?:bank\s+)?account\s*[*x•\s-]*(\d{4})|حساب\s*[*x•\s-]*(\d{4})/iu)
  const explicitAccountSuffix = accountSuffixMatch?.[1] ?? accountSuffixMatch?.[2] ?? null
  const cashSuffix = explicitAccountSuffix ?? (debitOrAccountHint ? cardSuffix : null)

  if (cashSuffix) {
    const matchingCashSources = cashSources.filter((item) => lastFour(item.account_identifier) === cashSuffix)
    const matchedCashSource = unique(matchingCashSources)
    if (matchedCashSource) return String(matchedCashSource.id)
  }

  if (cardSuffix && creditCardHint) {
    const matchedCard = unique(creditCards.filter((item) => lastFour(item.last4) === cardSuffix))
    if (matchedCard) return String(-matchedCard.id)
  }

  if (cardSuffix) {
    const matchingCashSources = cashSources.filter((item) => lastFour(item.account_identifier) === cardSuffix)
    const matchedCashSource = unique(matchingCashSources)
    if (matchedCashSource) return String(matchedCashSource.id)
    const matchedCard = unique(creditCards.filter((item) => lastFour(item.last4) === cardSuffix))
    if (matchedCard) return String(-matchedCard.id)
  }

  const namedCashSources = unique(cashSources.filter((item) =>
    hasNamedSource(text, item.account_name) || hasNamedSource(text, item.bank_name),
  ))
  if (namedCashSources) return String(namedCashSources.id)
  return null
}

/** Merchant-based expense suggestions; unknown merchants intentionally remain Other. */
export function suggestExpenseCategory(text: string) {
  const value = normalizedText(text)
  const rules: Array<[string, RegExp]> = [
    ['BANK_FEES', /bank\s+fee|service\s+fee|رسوم\s*(?:بنكية|إدارية)|عمولة\s*بنكية/u],
    ['UTILITIES', /\b(?:stc|mobily|zain|sal|sec|saudi\s+electricity|electricity|water\s+bill)\b|(?:الاتصالات|موبايلي|زين|الكهرباء|شركة\s+المياه)/u],
    ['SUBSCRIPTIONS', /\b(?:netflix|spotify|apple\.com\/bill|google\s*play|youtube\s*premium|shahid)\b|(?:نتفلكس|سبوتيفاي|اشتراك)/u],
    ['RIDE_HAILING', /\b(?:uber(?!\s*[* ]?eats)|careem|taxi|ride\s*hailing)\b|(?:أوبر(?!\s*إيتس)|كريم|سيارة\s*أجرة)/u],
    ['GROCERIES', /\b(?:panda|danube|carrefour|tamimi|lulu|othaim|grocery|supermarket)\b|(?:بنده|الدانوب|كارفور|التميمي|لولو|العثيم|بقالة|سوبرماركت)/u],
    ['DINING', /\b(?:uber\s*[* ]?eats|hungerstation|jahez|toyou|talabat|restaurant|cafe|coffee|starbucks|mcdonald.?s|kfc|pizza)\b|(?:هنقرستيشن|جاهز|طلبات|مطعم|مطاعم|كافيه|كوفي|قهوة)/u],
    ['FUEL', /\b(?:fuel|petrol|gas\s+station|aramex|aldrees|al\s+drees)\b|(?:وقود|بنزين|محطة\s*وقود|الدريس)/u],
    ['PHARMACY', /\b(?:pharmacy|nahdi|aldawaa|al\s+dawaa)\b|(?:صيدلية|النهدي|الدواء)/u],
    ['MEDICAL', /\b(?:hospital|clinic|medical|doctor|dentist)\b|(?:مستشفى|عيادة|طبي|طبيب|أسنان)/u],
    ['PARKING', /\b(?:parking|mauqif|mawgif)\b|(?:مواقف|موقف|رسوم\s*مواقف)/u],
    ['TRAVEL', /\b(?:airline|hotel|booking\.com|flynas|saudia|flyadeal)\b|(?:طيران|فندق|حجز\s*سفر)/u],
  ]
  return rules.find(([, pattern]) => pattern.test(value))?.[0] ?? 'OTHER'
}
