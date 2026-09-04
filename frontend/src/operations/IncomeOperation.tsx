/* eslint-disable react-hooks/set-state-in-effect */
import { AlertTriangle, Banknote, BriefcaseBusiness, CalendarDays, ChartNoAxesCombined, CheckCircle2, ChevronLeft, ChevronRight, House, Info, Landmark, Link2, Percent, Plus, ReceiptText, RotateCcw, Search, Shapes, Sparkles, WalletCards } from 'lucide-react'
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { createPortal } from 'react-dom'
import type { LucideIcon } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'

import { recordIncome, type PropertyAsset } from '../services/accountingService'
import './IncomeOperation.css'
import OperationPreflight from '../components/ui/OperationPreflight'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { usePortfolio } from '../hooks/usePortfolio'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { useLanguage } from '../context/LanguageContext'
import { useCurrency } from '../context/CurrencyContext'

type AccountingCategory = 'SALARY' | 'RENTAL' | 'DIVIDEND' | 'INTEREST' | 'BUSINESS' | 'CAPITAL_GAIN' | 'CASHBACK' | 'OTHER'
type IncomeTypeDefinition = { value: string; label: string; group: string; accountingSource: AccountingCategory; reference?: 'RENTAL' | 'DIVIDEND' | 'INTEREST'; icon: LucideIcon }
type StoredCustomIncomeType = Omit<IncomeTypeDefinition, 'icon'>

const incomeTypes: IncomeTypeDefinition[] = [
  { value: 'SALARY', label: 'الراتب', group: 'العمل', accountingSource: 'SALARY', icon: Banknote },
  { value: 'BONUS', label: 'المكافأة', group: 'العمل', accountingSource: 'SALARY', icon: Banknote },
  { value: 'COMMISSION', label: 'العمولة', group: 'العمل', accountingSource: 'SALARY', icon: Banknote },
  { value: 'ALLOWANCE', label: 'البدل', group: 'العمل', accountingSource: 'SALARY', icon: Banknote },
  { value: 'OVERTIME', label: 'العمل الإضافي', group: 'العمل', accountingSource: 'SALARY', icon: Banknote },
  { value: 'BUSINESS', label: 'أرباح الأعمال', group: 'الأعمال والعمل الحر', accountingSource: 'BUSINESS', icon: BriefcaseBusiness },
  { value: 'FREELANCE', label: 'العمل الحر', group: 'الأعمال والعمل الحر', accountingSource: 'BUSINESS', icon: BriefcaseBusiness },
  { value: 'CONSULTING', label: 'الاستشارات', group: 'الأعمال والعمل الحر', accountingSource: 'BUSINESS', icon: BriefcaseBusiness },
  { value: 'PARTNERSHIP', label: 'توزيعات الشراكة', group: 'الأعمال والعمل الحر', accountingSource: 'BUSINESS', icon: BriefcaseBusiness },
  { value: 'RENTAL', label: 'Residential Rent', group: 'Property', accountingSource: 'RENTAL', reference: 'RENTAL', icon: House },
  { value: 'COMMERCIAL_RENT', label: 'Commercial Rent', group: 'Property', accountingSource: 'RENTAL', reference: 'RENTAL', icon: House },
  { value: 'SHORT_TERM_RENT', label: 'Short-term Rent', group: 'Property', accountingSource: 'RENTAL', reference: 'RENTAL', icon: House },
  { value: 'DIVIDEND', label: 'توزيعات الأسهم', group: 'الاستثمارات', accountingSource: 'DIVIDEND', reference: 'DIVIDEND', icon: ChartNoAxesCombined },
  { value: 'FUND_DISTRIBUTION', label: 'توزيعات الصناديق', group: 'الاستثمارات', accountingSource: 'DIVIDEND', reference: 'DIVIDEND', icon: ChartNoAxesCombined },
  { value: 'SUKUK_INCOME', label: 'دخل الصكوك والكوبونات', group: 'الاستثمارات', accountingSource: 'INTEREST', reference: 'INTEREST', icon: Percent },
  { value: 'OPTION_PREMIUM', label: 'علاوة الخيارات', group: 'الاستثمارات', accountingSource: 'CAPITAL_GAIN', reference: 'DIVIDEND', icon: ChartNoAxesCombined },
  { value: 'CAPITAL_GAIN', label: 'الأرباح الرأسمالية', group: 'الاستثمارات', accountingSource: 'CAPITAL_GAIN', icon: ChartNoAxesCombined },
  { value: 'INTEREST', label: 'فوائد الودائع', group: 'الادخار والإقراض', accountingSource: 'INTEREST', reference: 'INTEREST', icon: Percent },
  { value: 'PRIVATE_LENDING', label: 'دخل الإقراض الخاص', group: 'الادخار والإقراض', accountingSource: 'INTEREST', icon: Percent },
  { value: 'P2P_YIELD', label: 'عائد الإقراض النظير', group: 'الادخار والإقراض', accountingSource: 'INTEREST', icon: Percent },
  { value: 'PENSION', label: 'المعاش', group: 'التقاعد والمزايا', accountingSource: 'OTHER', icon: Landmark },
  { value: 'GOVERNMENT_BENEFIT', label: 'الإعانات الحكومية', group: 'التقاعد والمزايا', accountingSource: 'OTHER', icon: Landmark },
  { value: 'ANNUITY', label: 'الدفعات السنوية', group: 'التقاعد والمزايا', accountingSource: 'OTHER', icon: Landmark },
  { value: 'ROYALTIES', label: 'حقوق الملكية', group: 'الملكية الفكرية', accountingSource: 'OTHER', icon: Shapes },
  { value: 'LICENSING', label: 'دخل التراخيص', group: 'الملكية الفكرية', accountingSource: 'OTHER', icon: Shapes },
  { value: 'CONTENT_REVENUE', label: 'إيرادات المحتوى', group: 'الملكية الفكرية', accountingSource: 'BUSINESS', icon: Shapes },
  { value: 'CASHBACK', label: 'استرداد نقدي', group: 'أخرى', accountingSource: 'CASHBACK', icon: WalletCards },
  { value: 'SUPPORT_PAYMENT', label: 'دفعات الدعم', group: 'أخرى', accountingSource: 'OTHER', icon: Shapes },
  { value: 'PRIZE', label: 'الجوائز والمكافآت', group: 'أخرى', accountingSource: 'OTHER', icon: Shapes },
  { value: 'OTHER', label: 'دخل آخر', group: 'أخرى', accountingSource: 'OTHER', icon: Shapes },
]

type IncomeType = string
const incomeTypeGroups = [...new Set(incomeTypes.map((type) => type.group))]
const defaultIncomeTypes: IncomeType[] = ['SALARY', 'RENTAL', 'DIVIDEND', 'INTEREST', 'BUSINESS', 'OTHER']
const incomeTypeDefinitions: Record<string, string> = {
  SALARY: 'Regular pay received from employment.', BONUS: 'Additional employment pay linked to performance or company results.', COMMISSION: 'Pay earned from sales or completed transactions.', ALLOWANCE: 'Employer-paid support for housing, transport, or other costs.', OVERTIME: 'Additional pay for hours worked beyond the regular schedule.',
  BUSINESS: 'Profit distributed or withdrawn from an owned business.', FREELANCE: 'Income earned from independent project-based work.', CONSULTING: 'Professional advisory fees earned from clients.', PARTNERSHIP: 'A share of profit distributed by a business partnership.',
  RENTAL: 'Rent received from residential property.', COMMERCIAL_RENT: 'Rent received from commercial property.', SHORT_TERM_RENT: 'Income from short-stay or holiday property rentals.',
  DIVIDEND: 'Cash distributions paid to shareholders.', FUND_DISTRIBUTION: 'Income distributed by an investment fund.', SUKUK_INCOME: 'Periodic income paid by sukuk or coupon-bearing investments.', OPTION_PREMIUM: 'Premium recognized from completed or realized options activity.', CAPITAL_GAIN: 'Profit realized when an asset is sold above its cost.',
  INTEREST: 'Return earned on bank deposits or savings balances.', PRIVATE_LENDING: 'Return earned from lending money privately.', P2P_YIELD: 'Return earned through peer-to-peer lending platforms.',
  PENSION: 'Recurring retirement income paid by a pension provider.', GOVERNMENT_BENEFIT: 'Financial support received from a government program.', ANNUITY: 'Contractual payments received periodically, often during retirement.',
  ROYALTIES: 'Income earned from the use of intellectual property.', LICENSING: 'Fees earned by granting rights to use an asset or creation.', CONTENT_REVENUE: 'Income earned from publishing, media, or digital content.',
  CASHBACK: 'A rebate received after eligible purchases.', SUPPORT_PAYMENT: 'Recurring financial support received from another party.', PRIZE: 'Money received from a prize, award, or competition.', OTHER: 'Income that does not fit another available category.',
}

const incomeTypeStorageKey = 'wealthos-active-income-types'
const customIncomeTypeStorageKey = 'wealthos-custom-income-types'
const propertyUsageLabels:Record<PropertyAsset['usage'],string>={PRIMARY_RESIDENCE:'Primary Residence',INVESTMENT_PROPERTY:'Investment Property',VACATION_HOME:'Vacation Home',OTHER:'Other',UNSPECIFIED:'Use Not Set'}
const propertyIncomeTabs:Record<NonNullable<PropertyAsset['income_type']>,IncomeType>={RESIDENTIAL_RENT:'RENTAL',COMMERCIAL_RENT:'COMMERCIAL_RENT',SHORT_TERM_RENT:'SHORT_TERM_RENT'}

function loadCustomIncomeTypes(): StoredCustomIncomeType[] {
  try {
    const stored = JSON.parse(localStorage.getItem(customIncomeTypeStorageKey) ?? '[]')
    if (Array.isArray(stored)) return stored.filter((type) => type?.value && type?.label && type?.accountingSource)
  } catch {
    // Invalid custom entries are ignored without affecting the standard catalog.
  }
  return []
}

function loadActiveIncomeTypes(): IncomeType[] {
  try {
    const stored = JSON.parse(localStorage.getItem(incomeTypeStorageKey) ?? 'null')
    if (Array.isArray(stored)) {
      const availableValues = [...incomeTypes.map((type) => type.value), ...loadCustomIncomeTypes().map((type) => type.value)]
      const valid = availableValues.filter((value) => stored.includes(value))
      if (valid.length) return valid
    }
  } catch {
    // Keep the complete set for existing workspaces when no valid preference exists.
  }
  return defaultIncomeTypes
}

type IncomeDraft = {
  destinationCode: string
  amount: string
  transactionDate: string
  description: string
  linkedSource: string
  assetQuery: string
  rentFrequency: 'MONTHLY'|'QUARTERLY'|'SEMI_ANNUAL'|'ANNUAL'
  nextRentDueDate: string
}

export default function IncomeOperation() {
  const {t}=useLanguage()
  const {formatMoney}=useCurrency()
  const imported=useImportedOperationDraft()
  const [searchParams]=useSearchParams()
  const financial=useFinancialSummary()
  const portfolio=usePortfolio('consolidated')
  const [properties,setProperties]=useState<PropertyAsset[]>([])
  const [activeIncomeSources, setActiveIncomeSources] = useState<IncomeType[]>(loadActiveIncomeTypes)
  const [incomeSource, setIncomeSource] = useState(() => {
    const active = loadActiveIncomeTypes()
    const requested=searchParams.get('type')
    if(requested&&incomeTypes.some(type=>type.value===requested))return requested
    return active.includes('DIVIDEND') ? 'DIVIDEND' : active[0]
  })
  const [incomeTypeMenuOpen, setIncomeTypeMenuOpen] = useState(false)
  const [incomeDefinitionsOpen, setIncomeDefinitionsOpen] = useState(false)
  const [incomeTypeSearch, setIncomeTypeSearch] = useState('')
  const [incomeTabStart, setIncomeTabStart] = useState(0)
  const [incomeTabHistory, setIncomeTabHistory] = useState<number[]>([])
  const [incomeTabStripWidth, setIncomeTabStripWidth] = useState(0)
  const incomeTabStripRef = useRef<HTMLDivElement>(null)
  const [customIncomeTypes, setCustomIncomeTypes] = useState<StoredCustomIncomeType[]>(loadCustomIncomeTypes)
  const [customIncomeName, setCustomIncomeName] = useState('')
  const [customAccountingCategory, setCustomAccountingCategory] = useState<AccountingCategory>('OTHER')
  const [headerActionsTarget, setHeaderActionsTarget] = useState<HTMLElement | null>(null)
  const [destinationCode, setDestinationCode] = useState('')
  const [amount, setAmount] = useState('')
  const [transactionDate, setTransactionDate] = useState('')
  const [description, setDescription] = useState('')
  const [linkedSource, setLinkedSource] = useState('')
  const [assetQuery, setAssetQuery] = useState('')
  const [drafts, setDrafts] = useState<Record<string, IncomeDraft>>({})
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState<{ tone: 'success' | 'error'; text: string } | null>(null)
  const [rentFrequency,setRentFrequency]=useState<'MONTHLY'|'QUARTERLY'|'SEMI_ANNUAL'|'ANNUAL'>('MONTHLY')
  const [nextRentDueDate,setNextRentDueDate]=useState('')

  useEffect(() => {
    const now = new Date()
    setTransactionDate(new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16))
    setHeaderActionsTarget(document.getElementById('income-operation-header-actions'))
  }, [])

  useEffect(()=>{
    if(!imported.draft)return
    const text=`${imported.draft.description} ${imported.draft.source_text}`.toLowerCase()
    const inferred=/rent|إيجار|ايجار/.test(text)?'RENTAL':/dividend|distribution|توزيع/.test(text)?'DIVIDEND':/interest|yield|فائدة|عائد/.test(text)?'INTEREST':/salary|راتب/.test(text)?'SALARY':'OTHER'
    if(!activeIncomeSources.includes(inferred))setActiveIncomeSources(current=>[...current,inferred])
    setIncomeSource(inferred)
    setAmount(imported.draft.amount==null?'':String(Math.abs(imported.draft.amount)))
    setTransactionDate(toLocalDateTime(imported.draft.transaction_date))
    setDescription(imported.draft.description)
  },[imported.draft,activeIncomeSources])

  useEffect(() => {
    localStorage.setItem(incomeTypeStorageKey, JSON.stringify(activeIncomeSources))
  }, [activeIncomeSources])

  useEffect(() => {
    localStorage.setItem(customIncomeTypeStorageKey, JSON.stringify(customIncomeTypes))
  }, [customIncomeTypes])

  useEffect(() => {
    if (!incomeTypeMenuOpen) return
    const scrollPosition = window.scrollY
    const pageWidth = document.documentElement.clientWidth
    const previousOverflow = document.body.style.overflow
    const previousPosition = document.body.style.position
    const previousTop = document.body.style.top
    const previousWidth = document.body.style.width
    document.body.style.overflow = 'hidden'
    document.body.style.position = 'fixed'
    document.body.style.top = `-${scrollPosition}px`
    document.body.style.width = `${pageWidth}px`
    return () => {
      document.body.style.overflow = previousOverflow
      document.body.style.position = previousPosition
      document.body.style.top = previousTop
      document.body.style.width = previousWidth
      window.scrollTo(0, scrollPosition)
    }
  }, [incomeTypeMenuOpen])

  useLayoutEffect(() => {
    const strip = incomeTabStripRef.current
    if (!strip) return
    const updateWidth = () => setIncomeTabStripWidth(strip.getBoundingClientRect().width)
    updateWidth()
    const observer = new ResizeObserver(updateWidth)
    observer.observe(strip)
    return () => observer.disconnect()
  }, [])

  const allIncomeTypes = useMemo<IncomeTypeDefinition[]>(() => [
    ...incomeTypes,
    ...customIncomeTypes.map((type) => ({ ...type, icon: Shapes })),
  ], [customIncomeTypes])
  const selectedType = allIncomeTypes.find((type) => type.value === incomeSource) ?? incomeTypes[0]
  const activeIncomeTypes = allIncomeTypes.filter((type) => activeIncomeSources.includes(type.value))
  const visibleTabStart = Math.min(incomeTabStart, Math.max(0, activeIncomeTypes.length - 1))
  const remainingIncomeTypes = activeIncomeTypes.slice(visibleTabStart)
  const estimatedTabWidth = (label: string) => Math.max(52, label.length * 6.05 + 18)
  const previousNavigationWidth = visibleTabStart > 0 ? 34 : 0
  const remainingTabsWidth = remainingIncomeTypes.reduce((total, type) => total + estimatedTabWidth(type.label), 0)
  const needsMoreNavigation = remainingTabsWidth > Math.max(180, incomeTabStripWidth - previousNavigationWidth)
  const usableTabWidth = Math.max(120, incomeTabStripWidth - previousNavigationWidth - (needsMoreNavigation ? 72 : 0))
  let visibleIncomeTypeCount = 0
  let occupiedTabWidth = 0
  for (const type of remainingIncomeTypes) {
    const width = estimatedTabWidth(type.label)
    if (visibleIncomeTypeCount > 0 && occupiedTabWidth + width > usableTabWidth) break
    occupiedTabWidth += width
    visibleIncomeTypeCount += 1
  }
  visibleIncomeTypeCount = Math.max(1, visibleIncomeTypeCount)
  const visibleIncomeTypes = remainingIncomeTypes.slice(0, visibleIncomeTypeCount)
  const hasPreviousIncomeTypes = visibleTabStart > 0
  const hasMoreIncomeTypes = visibleTabStart + visibleIncomeTypeCount < activeIncomeTypes.length
  const matchingIncomeTypes = allIncomeTypes.filter((type) =>
    `${type.label} ${type.group}`.toLowerCase().includes(incomeTypeSearch.trim().toLowerCase()),
  )
  const destinationAccounts=financial.data?.bank_accounts??[]
  const selectedAccount = destinationAccounts.find((account) => String(account.id) === destinationCode)
  const rentalProperties=properties.filter(item=>!item.income_type||propertyIncomeTabs[item.income_type]===incomeSource)
  const incomePositions=(portfolio.data?.positions??[]).filter(item=>selectedType.value==='FUND_DISTRIBUTION'?['ETF','REIT'].includes(item.security_type):!['ETF','REIT'].includes(item.security_type))
  const linkedSources:Record<string,string[]>={
    RENTAL:rentalProperties.map(item=>`${item.name} · ${t(propertyUsageLabels[item.usage])}`),
    DIVIDEND:incomePositions.map(item=>`${item.symbol} · ${item.name}`),
    INTEREST:financial.data?.deposits.map(item=>`${item.product_name} · ${item.provider_name}`)??[],
  }
  const sourceOptions = selectedType.reference ? linkedSources[selectedType.reference] : undefined
  const availableSources = sourceOptions ?? []
  const sourceOptionsKey=availableSources.join('\u0000')

  useEffect(()=>{if(financial.data?.properties)setProperties(financial.data.properties)},[financial.data?.properties])
  useEffect(()=>{
    const inferred=new Set<IncomeType>()
    for(const property of financial.data?.properties??[]){if(property.usage==='INVESTMENT_PROPERTY'&&property.income_type)inferred.add(propertyIncomeTabs[property.income_type])}
    if((financial.data?.deposits.length??0)>0)inferred.add('INTEREST')
    for(const position of portfolio.data?.positions??[]){inferred.add(['ETF','REIT'].includes(position.security_type)?'FUND_DISTRIBUTION':'DIVIDEND')}
    if(!inferred.size)return
    setActiveIncomeSources(current=>{const additions=[...inferred].filter(value=>!current.includes(value));return additions.length?[...current,...additions]:current})
  },[financial.data?.deposits,financial.data?.properties,portfolio.data?.positions])
  useEffect(()=>{const requested=searchParams.get('property');if(!requested)return;const property=properties.find(item=>item.reference===requested);if(property){setLinkedSource(property.reference);setAssetQuery(`${property.name} · ${t(propertyUsageLabels[property.usage])}`)}},[properties,searchParams,t])
  useEffect(()=>{const requested=searchParams.get('asset');if(!requested)return;const source=sourceOptionsKey.split('\u0000').find(item=>item.toLowerCase()===requested.toLowerCase());if(!source)return;const property=selectedType.reference==='RENTAL'?properties.find(item=>`${item.name} · ${t(propertyUsageLabels[item.usage])}`===source):undefined;setLinkedSource(property?.reference??source);setAssetQuery(source)},[properties,searchParams,selectedType.reference,sourceOptionsKey,t])
  const numericAmount = Number(amount || 0)

  function changeIncomeSource(nextSource: IncomeType) {
    if (nextSource === incomeSource) return

    const currentDraft: IncomeDraft = {
      destinationCode,
      amount,
      transactionDate,
      description,
      linkedSource,
      assetQuery,
      rentFrequency,
      nextRentDueDate,
    }
    setDrafts((current) => ({
      ...current,
      [incomeSource]: currentDraft,
    }))

    const nextDraft = drafts[nextSource]
    setIncomeSource(nextSource)
    setDestinationCode(nextDraft?.destinationCode ?? '')
    setAmount(nextDraft?.amount ?? '')
    setTransactionDate(nextDraft?.transactionDate ?? transactionDate)
    setDescription(nextDraft?.description ?? '')
    setLinkedSource(nextDraft?.linkedSource ?? '')
    setAssetQuery(nextDraft?.assetQuery ?? '')
    setRentFrequency(nextDraft?.rentFrequency ?? 'MONTHLY')
    setNextRentDueDate(nextDraft?.nextRentDueDate ?? '')
    setResult(null)
  }

  function toggleIncomeType(nextSource: IncomeType) {
    const isActive = activeIncomeSources.includes(nextSource)
    if (!isActive) {
      setActiveIncomeSources((current) => [...current, nextSource])
      setIncomeTabStart(activeIncomeSources.length)
      setIncomeTabHistory([])
      changeIncomeSource(nextSource)
      return
    }

    if (activeIncomeSources.length === 1) {
      setResult({ tone: 'error', text: 'Keep at least one income source available.' })
      setIncomeTypeMenuOpen(false)
      return
    }

    const draftAmount = nextSource === incomeSource
      ? numericAmount
      : Number(drafts[nextSource]?.amount || 0)
    if (draftAmount > 0) {
      setResult({ tone: 'error', text: 'Clear or record this draft before hiding its income source.' })
      setIncomeTypeMenuOpen(false)
      return
    }

    const remaining = activeIncomeSources.filter((source) => source !== nextSource)
    if (nextSource === incomeSource) changeIncomeSource(remaining[0]!)
    setActiveIncomeSources(remaining)
  }

  function addCustomIncomeType() {
    const label = customIncomeName.trim()
    if (!label) return
    const existing = allIncomeTypes.find((type) => type.label.toLowerCase() === label.toLowerCase())
    if (existing) {
      if (!activeIncomeSources.includes(existing.value)) {
        setActiveIncomeSources((current) => [...current, existing.value])
        setIncomeTabStart(activeIncomeSources.length)
        setIncomeTabHistory([])
      }
      changeIncomeSource(existing.value)
    } else {
      const value = `CUSTOM_${Date.now()}`
      setCustomIncomeTypes((current) => [...current, { value, label, group: 'Custom', accountingSource: customAccountingCategory }])
      setActiveIncomeSources((current) => [...current, value])
      setIncomeTabStart(activeIncomeSources.length)
      setIncomeTabHistory([])
      changeIncomeSource(value)
    }
    setCustomIncomeName('')
    setIncomeTypeSearch('')
    setIncomeTypeMenuOpen(false)
  }

  function selectSource(source: string) {
    const property=selectedType.reference==='RENTAL'?properties.find(item=>`${item.name} · ${t(propertyUsageLabels[item.usage])}`===source):undefined
    setLinkedSource(property?.reference ?? source)
    setAssetQuery(source)
  }

  const formattedAmount = formatMoney(numericAmount)

  const pendingDrafts = useMemo(() => allIncomeTypes
    .map((type) => {
      const draftAmount = type.value === incomeSource
        ? numericAmount
        : Number(drafts[type.value]?.amount || 0)
      return { value: type.value, label: type.label, amount: draftAmount }
    })
    .filter((draft) => draft.amount > 0), [allIncomeTypes, drafts, incomeSource, numericAmount])

  const pendingTotal = pendingDrafts.reduce(
    (total, draft) => total + draft.amount,
    0,
  )

  const formattedPendingTotal = formatMoney(pendingTotal)

  function clearCurrentFields() {
    const now = new Date()
    setDestinationCode('')
    setAmount('')
    setTransactionDate(new Date(now.getTime() - now.getTimezoneOffset() * 60000).toISOString().slice(0, 16))
    setDescription('')
    setLinkedSource('')
    setAssetQuery('')
    setRentFrequency('MONTHLY')
    setNextRentDueDate('')
    setResult(null)
    setDrafts((current) => {
      const next = { ...current }
      delete next[incomeSource]
      return next
    })
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (numericAmount <= 0 || !transactionDate || isSubmitting) return

    setIsSubmitting(true)
    setResult(null)

    const entryDescription = description.trim()
      || `${selectedType.label} income${linkedSource ? ` — ${linkedSource}` : ''}`

    try {
      const posted=await recordIncome({
        income_source: selectedType.value,
        accounting_category: selectedType.accountingSource,
        destination_account_code: 1120,
        destination_bank_account_id: Number(destinationCode),
        amount: numericAmount,
        transaction_date: transactionDate,
        description: entryDescription,
        linked_source: linkedSource || undefined,
        rent_frequency: selectedType.accountingSource==='RENTAL'&&linkedSource.startsWith('property:')?rentFrequency:undefined,
        next_rent_due_date: selectedType.accountingSource==='RENTAL'&&linkedSource.startsWith('property:')?nextRentDueDate:undefined,
        rent_property_name: selectedType.accountingSource==='RENTAL'?properties.find(item=>item.reference===linkedSource)?.name||assetQuery||undefined:undefined,
      })
      await imported.confirm(postingReference(posted,'income'),linkedSource?'ASSET':undefined)
      setResult({ tone: 'success', text: `${formattedAmount} recorded successfully in the ledger.` })
      setAmount('')
      setDescription('')
      setLinkedSource('')
      setAssetQuery('')
      setRentFrequency('MONTHLY')
      setNextRentDueDate('')
      setDrafts((current) => {
        const next = { ...current }
        delete next[incomeSource]
        return next
      })
    } catch (error) {
      setResult({
        tone: 'error',
        text: error instanceof Error ? error.message : t('Unable to record income.'),
      })
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="income-operation">
      {headerActionsTarget && createPortal(
        <div className={`income-operation__type-manager${incomeTypeMenuOpen ? ' is-open' : ''}`}>
          <button className="income-operation__manage-types" type="button" onClick={() => setIncomeTypeMenuOpen((open) => !open)}>
            <Plus size={15} /> إضافة مصدر دخل
          </button>
          {incomeTypeMenuOpen && (
            <div className="income-operation__type-overlay" onMouseDown={(event) => {
              if (event.currentTarget !== event.target) return
              setIncomeTypeMenuOpen(false)
              setIncomeDefinitionsOpen(false)
            }}>
            <div className="income-operation__type-menu">
              <div className="income-operation__catalog-heading"><div><strong>مصادر الدخل</strong><small>{incomeDefinitionsOpen ? 'دليل موجز لمصادر الدخل في هذا الدليل.' : 'اختر المصادر القياسية أو أنشئ مصدرًا خاصًا.'}</small></div><button className={incomeDefinitionsOpen ? 'is-active' : ''} type="button" title="تعريفات مصادر الدخل" aria-label="تعريفات مصادر الدخل" onClick={() => setIncomeDefinitionsOpen((open) => !open)}><Info size={17} /></button></div>
              {incomeDefinitionsOpen ? <div className="income-operation__definitions">
                {[...incomeTypeGroups, ...(customIncomeTypes.length ? ['مخصص'] : [])].map((group) => {
                  const groupTypes = allIncomeTypes.filter((type) => type.group === group)
                  return <section key={group}><h4>{group}</h4><p>{groupTypes.map((type, index) => <span key={type.value}><strong>{type.label}:</strong> {incomeTypeDefinitions[type.value] ?? 'مصدر دخل مخصص عرّفه المستخدم.'}{index < groupTypes.length - 1 ? ' ' : ''}</span>)}</p></section>
                })}
                <button type="button" onClick={() => setIncomeDefinitionsOpen(false)}>العودة إلى المصادر</button>
              </div> : <>
              <label className="income-operation__catalog-search"><Search size={15} /><input autoFocus placeholder="البحث في مصادر الدخل" value={incomeTypeSearch} onChange={(event) => setIncomeTypeSearch(event.target.value)} /></label>
              <div className="income-operation__catalog-list">
                {[...incomeTypeGroups, ...(customIncomeTypes.length ? ['مخصص'] : [])].map((group) => {
                  const groupedTypes = matchingIncomeTypes.filter((type) => type.group === group)
                  if (!groupedTypes.length) return null
                  return <section key={group}><h4>{group}</h4><div>{groupedTypes.map((type) => {
                    const TypeIcon = type.icon
                    const active = activeIncomeSources.includes(type.value)
                    return <button type="button" className={active ? 'is-active' : ''} onClick={() => toggleIncomeType(type.value)} key={type.value}>
                      <span><TypeIcon size={14} />{type.label}</span><em>{active ? 'ظاهر' : 'إضافة'}</em>
                    </button>
                  })}</div></section>
                })}
                {!matchingIncomeTypes.length && <p>لم يُعثر على مصادر مطابقة.</p>}
              </div>
              <div className="income-operation__custom-source">
                <div><strong>مصدر مخصص</strong><small>أنشئ مصدرًا غير مدرج أعلاه.</small></div>
                <input placeholder="اسم المصدر" value={customIncomeName} onChange={(event) => setCustomIncomeName(event.target.value)} />
                <select value={customAccountingCategory} onChange={(event) => setCustomAccountingCategory(event.target.value as AccountingCategory)}>
                  <option value="SALARY">دخل العمل</option><option value="BUSINESS">دخل الأعمال</option><option value="RENTAL">دخل الإيجار</option><option value="DIVIDEND">توزيعات الاستثمار</option><option value="INTEREST">الفوائد والعوائد</option><option value="CAPITAL_GAIN">ربح رأسمالي</option><option value="CASHBACK">استرداد نقدي</option><option value="OTHER">دخل آخر</option>
                </select>
                <button type="button" disabled={!customIncomeName.trim()} onClick={addCustomIncomeType}><Plus size={14} /> إضافة مصدر مخصص</button>
              </div>
              </>}
            </div>
            </div>
          )}
        </div>,
        headerActionsTarget,
      )}
      <form className="income-operation__form" onSubmit={handleSubmit}>
        <div className="income-operation__section-heading">
          <div><span>01</span><div><h3>تفاصيل الدخل</h3><p>حدد مصدر هذا المبلغ.</p></div></div>
          <Sparkles size={17} />
        </div>

        <fieldset className="income-operation__types">
          <legend>نوع الدخل</legend>
          <div className="income-operation__type-strip" ref={incomeTabStripRef}>
          {hasPreviousIncomeTypes && <button className="income-operation__tab-navigation is-previous" type="button" title="مصادر الدخل السابقة" onClick={() => {
            const previousStart = incomeTabHistory.at(-1) ?? Math.max(0, visibleTabStart - visibleIncomeTypeCount)
            setIncomeTabStart(previousStart)
            setIncomeTabHistory((history) => history.slice(0, -1))
          }}><ChevronLeft size={15} /></button>}
          <div className="income-operation__active-types">
            {visibleIncomeTypes.map((type) => {
              const TypeIcon = type.icon
              return (
                <button
                  className={incomeSource === type.value ? 'is-selected' : ''}
                  type="button"
                  title={type.label}
                  onClick={() => changeIncomeSource(type.value)}
                  key={type.value}
                >
                  <span><TypeIcon size={15} /></span><strong>{type.label}</strong>
                </button>
              )
            })}
          </div>
          {hasMoreIncomeTypes && <button className="income-operation__tab-navigation is-more" type="button" title="المزيد من مصادر الدخل" onClick={() => {
            setIncomeTabHistory((history) => [...history, visibleTabStart])
            setIncomeTabStart(visibleTabStart + visibleIncomeTypeCount)
          }}><strong>المزيد</strong><ChevronRight size={14} /></button>}
          </div>
        </fieldset>

        <div className="income-operation__fields income-operation__fields--two">
          <label>
            <span><WalletCards size={14} /> حساب الوجهة</span>
            <select value={destinationCode} onChange={(event) => setDestinationCode(event.target.value)}>
              <option value="">اختر الحساب البنكي</option>
              {destinationAccounts.map((account) => (
                <option value={account.id} key={account.id}>{account.account_name} · {account.bank_name}</option>
              ))}
            </select>
            <small>{selectedAccount?`${selectedAccount.account_type} · ${selectedAccount.currency_code}`:'أضف حسابًا بنكيًا أولًا.'}</small>
          </label>

          <label>
            <span>المبلغ</span>
            <div className="income-operation__amount">
              <span>ر.س</span>
              <input
                type="number"
                min="0.01"
                step="0.01"
                placeholder="0.00"
                value={amount}
                onChange={(event) => setAmount(event.target.value)}
                required
              />
            </div>
          </label>
        </div>

        <div className="income-operation__type-specific">
        {sourceOptions ? (
          <div className="income-operation__linked-source">
            <label htmlFor="related-asset"><span><Link2 size={14} /> {t('Related Asset')} <em>{t('Recommended')}</em></span></label>
            <select id="related-asset" value={assetQuery} onChange={(event) => event.target.value ? selectSource(event.target.value) : selectSource('')}>
              <option value="">{t('Select Related Asset')}</option>
              {availableSources.map((source) => <option value={source} key={source}>{source}</option>)}
            </select>

            {linkedSource && (
              <div className="income-operation__asset-selection">
                <CheckCircle2 size={14} /> {t('Linked to')} <strong>{assetQuery || linkedSource}</strong>
              </div>
            )}

            {selectedType.accountingSource==='RENTAL'&&<div className="income-operation__rental-schedule">
              <label><span><CalendarDays size={14}/> {t('Rent Frequency')}</span><select value={rentFrequency} onChange={(event)=>setRentFrequency(event.target.value as typeof rentFrequency)} disabled={!linkedSource.startsWith('property:')}><option value="MONTHLY">{t('Monthly')}</option><option value="QUARTERLY">{t('Quarterly')}</option><option value="SEMI_ANNUAL">{t('Semi-annual')}</option><option value="ANNUAL">{t('Annual')}</option></select></label>
              <label><span><CalendarDays size={14}/> {t('Next Rent Due Date')}</span><input type="date" value={nextRentDueDate} onChange={(event)=>setNextRentDueDate(event.target.value)} required={linkedSource.startsWith('property:')} disabled={!linkedSource.startsWith('property:')}/></label>
            </div>}

          </div>
        ) : (
          <div className="income-operation__type-note">
            <CheckCircle2 size={16} />
            <p><strong>لا يلزم أصل مرتبط</strong>يمكن تسجيل دخل {t(selectedType.label)} مباشرة في الحساب المحدد.</p>
          </div>
        )}
        </div>

        <div className="income-operation__fields income-operation__fields--two">
          <label>
            <span><CalendarDays size={14} /> تاريخ المعاملة</span>
            <input type="datetime-local" value={transactionDate} onChange={(event) => setTransactionDate(event.target.value)} required />
          </label>
          <label>
            <span><ReceiptText size={14} /> الوصف <em>اختياري</em></span>
            <input type="text" maxLength={255} placeholder={`دخل ${t(selectedType.label)}`} value={description} onChange={(event) => setDescription(event.target.value)} />
          </label>
        </div>

        {result && <div className={`income-operation__message is-${result.tone}`}>{result.tone === 'success' ? <CheckCircle2 size={17} /> : <AlertTriangle size={17} />}{result.text}</div>}

        <div className="income-operation__actions">
          <span>يُنشئ قيد يومية متوازنًا تلقائيًا.</span>
          <div>
            <button className="is-secondary" type="button" disabled={isSubmitting} onClick={clearCurrentFields}>
              <RotateCcw size={15} /> مسح الحقول
            </button>
            <button type="submit" disabled={numericAmount <= 0 || !transactionDate || isSubmitting}>
              {isSubmitting ? 'جارٍ التسجيل…' : 'تسجيل الدخل'}
            </button>
          </div>
        </div>
      </form>

      <aside className="income-operation__summary">
        <div className="income-operation__summary-header">
          <span><Landmark size={18} /></span>
          <div><h3>معاينة المعاملة</h3><p>أثر القيد المزدوج</p></div>
        </div>

        <div className="income-operation__preview-amount">
          <span>إجمالي مسودات الدخل</span>
          <strong>{formattedPendingTotal}</strong>
          <small>تم إدخال {pendingDrafts.length} من أنواع الدخل</small>
        </div>

        <div className="income-operation__draft-summary">
          <div><span>تفصيل الدخل</span><strong>{pendingDrafts.length}</strong></div>
          {pendingDrafts.length ? pendingDrafts.map((draft) => (
            <p className={draft.value === incomeSource ? 'is-current' : ''} key={draft.value}>
              <span>{draft.label}{draft.value === incomeSource ? ' · الحالي' : ''}</span>
              <strong>{formatMoney(draft.amount)}</strong>
            </p>
          )) : <small>لم تُدخل مبالغ بعد.</small>}
          <small>يسجل زر الدخل التبويب الحالي فقط، وتظل المسودات الأخرى متاحة.</small>
        </div>

        <div className="income-operation__journal">
          <div className="income-operation__journal-title"><span>قيد اليومية</span><small>متوازن</small></div>
          <div><span><i className="is-debit">مدين</i>{selectedAccount?.account_name}</span><strong>{formattedAmount}</strong></div>
          <div><span><i className="is-credit">دائن</i>دخل {t(selectedType.label)}</span><strong>{formattedAmount}</strong></div>
        </div>

        <div className="income-operation__effects">
          <h4>الأثر المالي</h4>
          <p><span>قائمة المركز المالي</span><strong className="is-positive">زيادة الأصول</strong></p>
          <p><span>التدفق النقدي</span><strong className="is-positive">تدفق نقدي داخل</strong></p>
        </div>

        <OperationPreflight requiredComplete={numericAmount>0&&Boolean(transactionDate)&&Boolean(destinationCode)} balanced={numericAmount>0&&Boolean(destinationCode)} recorded={result?.tone==='success'}/>

        <div className="income-operation__smart-note">
          <Sparkles size={16} />
          <p><strong>تتبع المرجع</strong>يُحفظ المرجع المرتبط المحدد مع قيد اليومية للمراجعة لاحقًا.</p>
        </div>
      </aside>
    </div>
  )
}
