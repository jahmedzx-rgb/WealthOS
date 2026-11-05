import { useEffect, useMemo, useState } from 'react'
import { Activity, CalendarDays, ChevronLeft, ChevronRight, ReceiptText, Search } from 'lucide-react'
import PageNavigation from '../components/ui/PageNavigation'
import LookupSelect from '../components/LookupSelect'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { getMonthlyActivity, type FinancialActivity } from '../services/accountingService'
import './RecentActivityPage.css'
import './RecentActivityPage.rtl.css'
import './RecentActivityLinks.css'
import './RecentActivityMonth.css'
import { activityDetail, activityTitle } from '../utils/activityLabels'
import { formatDate, formatDateTime } from '../utils/dateFormat'
import { useLanguage } from '../context/LanguageContext'
import { Link } from 'react-router-dom'
import { displayLocale } from '../utils/localeFormat'

function normalizeSearch(value:string){return value.replace(/[٠-٩۰-۹]/g,character=>String(character.charCodeAt(0)-(character>='۰'?1776:1632))).replace(/٫/g,'.').replace(/[٬,]/g,'').toLowerCase().trim()}

export default function RecentActivityPage(){
  const {formatMoney}=useCurrency()
  const {t,language}=useLanguage()
  const now=new Date()
  const [period,setPeriod]=useState(()=>({year:now.getFullYear(),month:now.getMonth()+1}))
  const [activity,setActivity]=useState<FinancialActivity[]>([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  const [filters,setFilters]=useState<string[]>([])
  const [dateFilter,setDateFilter]=useState('All')
  const [query,setQuery]=useState('')
  useEffect(()=>{let live=true;setLoading(true);setError('');getMonthlyActivity(period.year,period.month).then(items=>{if(live)setActivity(items)}).catch(reason=>{if(live){setActivity([]);setError(reason instanceof Error?reason.message:'Unable to load activity.')}}).finally(()=>{if(live)setLoading(false)});return()=>{live=false}},[period])
  const items=useMemo(()=>activity.map((item)=>{const reference=item.related_reference??'';const depositWithdrawal=reference.startsWith('deposit-withdrawal:');const principalReturn=reference.endsWith(':principal-return')||depositWithdrawal;const openingPortfolio=reference.startsWith('opening-portfolio:')||reference.startsWith('opening-portfolio-adjustment:');const cardToCard=reference.startsWith('credit-card-sadad:');const amount=item.display_amount??item.cash_change;const cardCashback=reference.startsWith('credit-card-cashback:');const cardExpense=reference.startsWith('credit-card-expense:');const setup=reference.startsWith('portfolio-created:')||reference.startsWith('bank-account-created:')||reference.startsWith('credit-card-created:')||reference.startsWith('deposit-created:');const depositReturn=reference.startsWith('deposit-return:');const depositMaturityIncome=reference.startsWith('deposit-maturity:')&&reference.endsWith(':income');const realizedReturn=item.return_status==='REALIZED';const accruedReturn=depositReturn&&!realizedReturn;const openingDescription=/^(?:Opening balance|رصيد افتتاحي)\s*·/i.test(item.description);const legacyDepositOpening=reference.startsWith('deposit:')&&/^Opening deposit balance\s*·/i.test(item.description);const adjustment=reference.startsWith('opening-')||reference.startsWith('loan-opening:')||reference.includes('-adjustment:')||reference.startsWith('accounting-reclassification:')||(reference.startsWith('credit-card:')&&openingDescription)||legacyDepositOpening;const kind=setup?'Setup':accruedReturn?'Accrued Return':realizedReturn||cardCashback||depositMaturityIncome?'Income':cardExpense?'Expense':adjustment?'Adjustment':reference.startsWith('deposit:')||principalReturn||cardToCard?'Transfer':item.cash_change>0?'Income':item.cash_change<0?'Expense':'Transfer';return {...item,amount,principalReturn,neutralAmount:principalReturn||openingPortfolio||cardToCard,title:activityTitle(item,language),detail:activityDetail(item,language),kind}}),[activity,language])
  const availableDates=useMemo(()=>[...new Set(items.map(item=>item.transaction_date.slice(0,10)))].sort((a,b)=>b.localeCompare(a)),[items])
  const visible=useMemo(()=>{const needle=normalizeSearch(query);return items.filter(item=>{const searchable=normalizeSearch(`${item.title} ${item.detail} ${item.account_detail??''} ${item.amount} ${Math.abs(item.amount).toFixed(2)} ${formatMoney(item.amount)} ${item.transaction_date} ${formatDateTime(item.transaction_date)} ${item.id} ${item.related_reference??''}`);return(!filters.length||filters.includes(item.kind))&&(dateFilter==='All'||item.transaction_date.startsWith(dateFilter))&&searchable.includes(needle)})},[items,filters,dateFilter,query,formatMoney])
  const currentPeriod=period.year===now.getFullYear()&&period.month===now.getMonth()+1
  const monthLabel=new Intl.DateTimeFormat(displayLocale(language),{month:'long',year:'numeric'}).format(new Date(period.year,period.month-1,1))
  function toggleFilter(value:string){if(value==='All'){setFilters([]);return}setFilters(current=>current.includes(value)?current.filter(item=>item!==value):[...current,value])}
  function moveMonth(change:number){setPeriod(current=>{const date=new Date(current.year,current.month-1+change,1);return{year:date.getFullYear(),month:date.getMonth()+1}});setFilters([]);setDateFilter('All');setQuery('')}
  return <section className="activity-page">
    <header><PageNavigation/><div className="activity-page__identity"><span><Activity size={21}/></span><div><p>{t('Financial timeline')}</p><h1>{t('Recent Activity')}</h1><small>{t('One clear timeline for posted movements across your wealth.')}</small></div></div><nav className="activity-page__month" aria-label={t('Activity month')}><button type="button" onClick={()=>moveMonth(-1)} aria-label={t('Previous month')}><ChevronLeft size={16}/></button><div><small>{t(currentPeriod?'Current Month':'Activity Month')}</small><strong>{monthLabel}</strong></div><button type="button" disabled={currentPeriod} onClick={()=>moveMonth(1)} aria-label={t('Next month')}><ChevronRight size={16}/></button></nav></header>
    <div className="activity-page__metrics"><article><span>{t('Total activity')}</span><strong>{items.length}</strong><small>{monthLabel}</small></article><article><span>{t('Money in')}</span><strong>{items.filter(item=>item.kind==='Income').length}</strong><small>{t('Income events')}</small></article><article><span>{t('Money out')}</span><strong>{items.filter(item=>item.kind==='Expense').length}</strong><small>{t('Outgoing events')}</small></article></div>
    <section className="activity-page__panel">
      <div className="activity-page__toolbar"><section><label><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t('Search activity')}/></label><div className="activity-page__date-picker"><CalendarDays size={15}/><LookupSelect label={t('Filter by date')} value={dateFilter} options={[{value:'All',label:t('All Dates')},...availableDates.map(date=>({value:date,label:formatDate(date)}))]} searchable={false} menuPlacement="bottom" onChange={setDateFilter}/></div></section><div>{['All','Income','Expense','Accrued Return','Transfer','Adjustment','Setup'].map(value=>{const active=value==='All'?!filters.length:filters.includes(value);return <button className={active?'is-active':''} aria-pressed={active} type="button" onClick={()=>toggleFilter(value)} key={value}>{t(value)}</button>})}</div></div>
      <div className="activity-page__list"><div className="activity-page__list-head"><strong>{t('Type')}</strong><strong>{t('Operation and description')}</strong><strong>{t('Classification')}</strong><strong>{t('Amount and date')}</strong></div>{visible.map(item=>{const kindClass=item.kind.toLowerCase().replaceAll(' ','-');return <Link className="activity-page__entry-link" to={item.activity_url??`/activity/${item.id}`} key={`${item.related_reference}-${item.id}`}><article><span className={`activity-page__icon is-${kindClass}`}><ReceiptText size={18}/></span><div><strong>{item.title}</strong>{item.account_detail?<small>{item.account_detail}</small>:null}<small>{item.detail}</small></div><em className={`is-${kindClass}`}>{t(item.kind)}</em><div className="activity-page__value"><strong className={item.neutralAmount?'':item.amount>0?'is-positive':item.amount<0?'is-negative':''}><FormattedMoney value={formatMoney(item.amount,(item.currency_code??'SAR') as Currency)} sign={!item.neutralAmount&&item.amount>0?'+':''}/></strong><small>{formatDateTime(item.transaction_date)}</small></div></article></Link>})}{!loading&&!visible.length&&<div className="activity-page__empty"><Activity size={22}/><strong>{t(error?'Unable to load activity.':'No Posted Activity')}</strong><span>{error||t('Completed operations will appear here.')}</span></div>}</div>
    </section>
  </section>
}
