import { CalendarClock, Landmark } from 'lucide-react'
import { cardDaysUntil } from '../utils/cardDueDate'
import { cardReminderStage } from '../utils/cardReminder'
import { prioritySource } from '../utils/prioritySource'
import { useEffect, useState } from 'react'

import type { FocusItem } from '../components/dashboard/FocusToday'
import { getFinancialSummary, getRentalReminders } from '../services/accountingService'
import { getDistributionReminders } from '../services/notificationService'
import type { Currency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'


export function useLiveFocusItems() {
  const {language}=useLanguage()
  const [items, setItems] = useState<FocusItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)

  useEffect(() => {
    let active = true
    let inFlight = false
    let financial: Awaited<ReturnType<typeof getFinancialSummary>> | null = null
    let distributions: Awaited<ReturnType<typeof getDistributionReminders>> = []
    let rentals: Awaited<ReturnType<typeof getRentalReminders>> = []
    const refresh = () => {
      if (inFlight) return
      inFlight = true
      void Promise.allSettled([getFinancialSummary(), getDistributionReminders(30), getRentalReminders(30)])
      .then(([financialResult, distributionResult, rentalResult]) => {
        if (!active) return
        financial = prioritySource(financialResult, financial)
        distributions = prioritySource(distributionResult, distributions)
        rentals = prioritySource(rentalResult, rentals)
        setError([financialResult, distributionResult, rentalResult].some(result => result.status === 'rejected'))
        const cards: FocusItem[] = (financial?.credit_cards ?? []).flatMap((card):FocusItem[] => {
            const daysUntil=cardDaysUntil(card.payment_due_date, new Date(), card.payment_due_day)
            const issued=Number(card.issued_statement_balance??card.statement_balance)
            const paid=Boolean(card.statement_paid)||Number(card.statement_balance)<=0
            if(paid)return[]
            const stage=cardReminderStage(daysUntil,Boolean(card.statement_is_estimated),issued)
            if(!stage)return[]
            const title=language==='ar'?(stage==='issued'?'صدر كشف البطاقة':stage==='fifteen'?'تذكير بسداد البطاقة':stage==='five'?'التنبيه الأخير لسداد البطاقة':stage==='due'?'استحقاق البطاقة اليوم':'تأخر سداد البطاقة'):(stage==='issued'?'Card Statement Issued':stage==='fifteen'?'Card Payment Reminder':stage==='five'?'Final Card Payment Reminder':stage==='due'?'Card Payment Due Today':'Card Payment Overdue')
            const timing=daysUntil===null?'':daysUntil<0?(language==='ar'?`متأخر ${Math.abs(daysUntil)} يوم`:`${Math.abs(daysUntil)} days overdue`):daysUntil===0?(language==='ar'?'الاستحقاق اليوم':'Due today'):(language==='ar'?`متبقي ${daysUntil} يوم`:`${daysUntil} days remaining`)
            return [{
            id: `card-${card.id}-${card.statement_cutoff_date??'legacy'}-${stage}`,
            title,
            subtitle: `${card.issuer_bank} · ${card.card_name} • ${timing}`,
            paymentStatus: 'unpaid',
            amount: Number(card.statement_balance),
            amountCurrency: card.currency_code as Currency,
            bankName: card.issuer_bank,
            priority: stage==='overdue'||stage==='due'||stage==='five'?'high':stage==='fifteen'?'medium':'low',
            icon: <CalendarClock size={18}/>,
            route: `/operations/card-payment?card=${card.id}`,
          }]
          })
        const reminders: FocusItem[] = distributions.map((item) => ({
          id: `distribution-${item.announcement_id ?? `${item.position_id}-${item.distribution_date}`}`,
          title: language==='ar'
            ? (item.days_until<=0?'توزيع مستحق':'توزيع قادم')
            : (item.days_until<=0?'Distribution Due':'Upcoming Distribution'),
          subtitle: `${item.symbol} • ${item.days_until < 0
            ? (language==='ar'?`متأخر ${Math.abs(item.days_until)} يوم`:`${Math.abs(item.days_until)} Days Overdue`)
            : item.days_until === 0
              ? (language==='ar'?'اليوم':'Today')
              : item.days_until === 1
                ? (language==='ar'?'غدًا':'Tomorrow')
                : (language==='ar'?`خلال ${item.days_until} أيام`:`In ${item.days_until} Days`)}`,
          amount: item.expected_net_amount ?? item.expected_amount ?? undefined,
          amountCurrency: item.currency_code as Currency,
          priority: item.days_until <= 2 ? 'high' : item.days_until <= 7 ? 'medium' : 'low',
          icon: <Landmark size={18}/>,
          route: '/investing/cash-flows',
        }))
        const rentalItems:FocusItem[]=rentals.map(item=>({id:`rent-${item.id}`,title:'Rent Collection',subtitle:`${item.property_name} • ${item.days_until<0?`Overdue By ${Math.abs(item.days_until)} Days`:item.days_until===0?'Due Today':item.days_until===1?'Due Tomorrow':`Due In ${item.days_until} Days`}`,amount:item.expected_amount,priority:item.days_until<=2?'high':item.days_until<=7?'medium':'low',icon:<Landmark size={18}/>,route:`/operations/income?type=RENTAL&property=${encodeURIComponent(item.property_reference)}`}))
        if (active) setItems([...rentalItems, ...reminders, ...cards])
      })
      .catch(() => { if (active) setError(true) })
      .finally(() => { inFlight = false; if (active) setLoading(false) })
    }
    refresh()
    window.addEventListener('focus', refresh)
    const timer = window.setInterval(refresh, 60000)
    return () => { active = false; window.removeEventListener('focus', refresh); window.clearInterval(timer) }
  }, [language])

  return { items, loading, error }
}
