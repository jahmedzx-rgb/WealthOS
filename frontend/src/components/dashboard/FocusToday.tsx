import {
  ChevronLeft,
  ChevronRight,
  ArrowRight,
  CalendarClock,
} from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useNavigate } from 'react-router-dom'

import Card from '../ui/Card'
import FormattedMoney from '../ui/FormattedMoney'
import { useCurrency, type Currency } from '../../context/CurrencyContext'
import { useLiveFocusItems } from '../../hooks/useLiveFocusItems'

import './FocusToday.css'
import { useLanguage } from '../../context/LanguageContext'

export type FocusItem = {
  id: string
  title: string
  subtitle: string
  amount?: number
  amountCurrency?: Currency
  priority: 'high' | 'medium' | 'low'
  icon: React.ReactNode
  route: string
}

export default function FocusToday() {
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const navigate=useNavigate()
  const {items:focusItems}=useLiveFocusItems()
  const pageSize=4
  const[page,setPage]=useState(1)
  const[completed,setCompleted]=useState<string[]>([])
  const activeItems=focusItems.slice(0,8).filter(item=>!completed.includes(item.id))
  const totalPages=Math.max(1,Math.ceil(activeItems.length/pageSize))
  const currentPage=Math.min(page,totalPages)
  const pageItems=activeItems.slice((currentPage-1)*pageSize,currentPage*pageSize)
  function handleOpen(item:FocusItem){navigate(item.route)}
  function toggleHiddenItems(){setCompleted(activeItems.length===0?[]:focusItems.slice(0,8).map((item)=>item.id));setPage(1)}
  return (
    <Card
      icon={CalendarClock}
      title={t('Priorities')}
      action={
        <div className="focus-today__top-nav"><span className="focus-today__count">{activeItems.length} {t('items')}</span><button type="button" disabled={currentPage===1} onClick={()=>setPage(value=>value-1)} aria-label={t('Previous Focus page')}><ChevronLeft size={13}/></button><strong>{currentPage}/{totalPages}</strong><button type="button" disabled={currentPage===totalPages} onClick={()=>setPage(value=>value+1)} aria-label={t('Next Focus page')}><ChevronRight size={13}/></button><Link to="/focus">{t('View all')} <ArrowRight size={14}/></Link></div>
      }
    >
      <div className="focus-today">
        <div className={`focus-today__columns${activeItems.length===0?' is-hide-active':''}`}>
          <span>{t('Operation')}</span>
          <span>{t('Amount')}</span>
          <label title={t(activeItems.length===0?'Restore Hidden Priorities':'Hide All Priorities')}><input type="checkbox" aria-label={t(activeItems.length===0?'Restore Hidden Priorities':'Hide All Priorities')} checked={activeItems.length===0} onChange={toggleHiddenItems}/><span>{t(activeItems.length===0?'Restore All':'Hide All')}</span></label>
        </div>
        {pageItems.map((item) => (
          <div
            key={item.id}
            className="focus-today__item"
          >
            <div
              className={`focus-today__icon focus-today__icon--${item.priority}`}
            >
              {item.icon}
            </div>

            <div className="focus-today__content">
              <div className="focus-today__title">
                {item.title}
              </div>

              <div className="focus-today__subtitle">
                <CalendarClock size={14} />
                {item.subtitle}
              </div>

            </div>

            <div className={`focus-today__amount${item.amount===undefined?' is-empty':''}`}>
              {item.amount === undefined ? '—' : <FormattedMoney value={formatMoney(item.amount, item.amountCurrency ?? 'SAR')}/>} 
            </div>

            <button
              className="focus-today__complete"
              type="button"
              title={t('Open Operation')}
              aria-label={`${t('Open')} ${item.title}`}
              onClick={()=>handleOpen(item)}
            >
              <ArrowRight size={18} />
            </button>
          </div>
        ))}
        <footer className="focus-today__footer">
          <div className={`focus-today__end ${currentPage===totalPages?'':'is-placeholder'}`}><span/><small>{t(activeItems.length?'That’s everything for now':'You’re all caught up')}</small><span/></div>
        </footer>
      </div>
    </Card>
  )
}
