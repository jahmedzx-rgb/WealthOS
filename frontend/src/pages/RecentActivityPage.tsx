import { useMemo, useState } from 'react'
import { Activity, ReceiptText, Search } from 'lucide-react'
import PageNavigation from '../components/ui/PageNavigation'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency } from '../context/CurrencyContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import './RecentActivityPage.css'
import './RecentActivityPage.rtl.css'
import { activityDetail, activityTitle } from '../utils/activityLabels'
import { formatDateTime } from '../utils/dateFormat'
import { useLanguage } from '../context/LanguageContext'

export default function RecentActivityPage(){
  const financial=useFinancialSummary()
  const {formatMoney}=useCurrency()
  const {t,language}=useLanguage()
  const [filter,setFilter]=useState('All')
  const [query,setQuery]=useState('')
  const items=useMemo(()=>(financial.data?.recent_activity??[]).map((item)=>({...item,title:activityTitle(item,language),detail:activityDetail(item,language),kind:item.cash_change>0?'Income':item.cash_change<0?'Expense':'Transfer'})),[financial.data,language])
  const visible=useMemo(()=>items.filter(item=>(filter==='All'||item.kind===filter)&&`${item.title} ${item.detail}`.toLowerCase().includes(query.toLowerCase())),[items,filter,query])
  return <section className="activity-page">
    <header><PageNavigation/><div className="activity-page__identity"><span><Activity size={21}/></span><div><p>{t('Financial timeline')}</p><h1>{t('Recent Activity')}</h1><small>{t('One clear timeline for posted movements across your wealth.')}</small></div></div></header>
    <div className="activity-page__metrics"><article><span>{t('Total activity')}</span><strong>{items.length}</strong><small>{t('Latest posted events')}</small></article><article><span>{t('Money in')}</span><strong>{items.filter(item=>item.cash_change>0).length}</strong><small>{t('Income events')}</small></article><article><span>{t('Money out')}</span><strong>{items.filter(item=>item.cash_change<0).length}</strong><small>{t('Outgoing events')}</small></article></div>
    <section className="activity-page__panel">
      <div className="activity-page__toolbar"><label><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('Search activity')}/></label><div>{['All','Income','Expense','Transfer'].map(value=><button className={filter===value?'is-active':''} type="button" onClick={()=>setFilter(value)} key={value}>{t(value)}</button>)}</div></div>
      <div className="activity-page__list">{visible.map(item=><article key={item.id}><span className={`activity-page__icon is-${item.kind.toLowerCase()}`}><ReceiptText size={18}/></span><div><strong>{item.title}</strong><small>{item.detail}</small></div><em>{t(item.kind)}</em><div className="activity-page__value"><strong className={item.cash_change>0?'is-positive':item.cash_change<0?'is-negative':''}><FormattedMoney value={formatMoney(item.cash_change)} sign={item.cash_change>0?'+':''}/></strong><small>{formatDateTime(item.transaction_date)}</small></div></article>)}{!financial.loading&&!visible.length&&<div className="activity-page__empty"><Activity size={22}/><strong>{t('No Posted Activity')}</strong><span>{t('Completed operations will appear here.')}</span></div>}</div>
    </section>
  </section>
}
