import { CreditCard, Landmark } from 'lucide-react'
import { useEffect, useState } from 'react'

import type { FocusItem } from '../components/dashboard/FocusToday'
import { getFinancialSummary, getRentalReminders } from '../services/accountingService'
import { getDistributionReminders } from '../services/notificationService'
import type { Currency } from '../context/CurrencyContext'

const nextMonthlyDay = (day:number) => {
  const now=new Date()
  const date=new Date(now.getFullYear(),now.getMonth(),Math.min(day,new Date(now.getFullYear(),now.getMonth()+1,0).getDate()))
  return Math.ceil((date.getTime()-new Date(now.getFullYear(),now.getMonth(),now.getDate()).getTime())/86400000)
}

export function useLiveFocusItems() {
  const [items, setItems] = useState<FocusItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([getFinancialSummary(), getDistributionReminders(30), getRentalReminders(30)])
      .then(([financial, distributions, rentals]) => {
        const cards: FocusItem[] = financial.credit_cards
          .filter((card) => card.statement_balance > 0)
          .map((card):FocusItem => {
            const daysUntil=card.payment_due_day?nextMonthlyDay(card.payment_due_day):null
            const dueLabel=daysUntil===null?'Payment Date Not Set':daysUntil<0?`Overdue By ${Math.abs(daysUntil)} Days`:daysUntil===0?'Due Today':daysUntil===1?'Due Tomorrow':`Due in ${daysUntil} Days`
            return ({
            id: `card-${card.id}`,
            title: 'Credit Card Settlement',
            subtitle: `${card.card_name} • ${dueLabel}`,
            amount: card.statement_balance,
            amountCurrency: card.currency_code as Currency,
            priority: daysUntil!==null&&daysUntil<=3?'high':daysUntil!==null&&daysUntil<=7?'medium':'low',
            icon: <CreditCard size={18}/>,
            route: `/operations/card-payment?card=${card.id}`,
          })}).filter(item=>{const match=item.subtitle.match(/Due in (\d+) Days/i);return !match||Number(match[1])<=7})
        const reminders: FocusItem[] = distributions.map((item) => ({
          id: `distribution-${item.position_id}-${item.distribution_date}`,
          title: 'Upcoming Distribution',
          subtitle: `${item.symbol} • ${item.days_until === 0 ? 'Today' : item.days_until === 1 ? 'Tomorrow' : `In ${item.days_until} Days`}`,
          amount: item.expected_amount ?? undefined,
          amountCurrency: item.currency_code as Currency,
          priority: item.days_until <= 2 ? 'high' : item.days_until <= 7 ? 'medium' : 'low',
          icon: <Landmark size={18}/>,
          route: `/portfolios/${item.portfolio_id}/positions/${item.security_id}`,
        }))
        const rentalItems:FocusItem[]=rentals.map(item=>({id:`rent-${item.id}`,title:'Rent Collection',subtitle:`${item.property_name} • ${item.days_until<0?`Overdue By ${Math.abs(item.days_until)} Days`:item.days_until===0?'Due Today':item.days_until===1?'Due Tomorrow':`Due In ${item.days_until} Days`}`,amount:item.expected_amount,priority:item.days_until<=2?'high':item.days_until<=7?'medium':'low',icon:<Landmark size={18}/>,route:`/operations/income?type=RENTAL&property=${encodeURIComponent(item.property_reference)}`}))
        setItems([...rentalItems, ...reminders, ...cards])
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false))
  }, [])

  return { items, loading }
}
