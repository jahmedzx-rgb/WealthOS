import { CalendarClock, CheckCircle2, ListTodo } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageNavigation from '../components/ui/PageNavigation'
import { useLiveFocusItems } from '../hooks/useLiveFocusItems'
import { useLanguage } from '../context/LanguageContext'
import './FocusPage.css'
import './FocusPageComfort.css'
import { formatDisplayNumber } from '../utils/localeFormat'
import BankIdentity from '../components/ui/BankIdentity'

export default function FocusPage(){
  const navigate=useNavigate()
  const {items,loading,error}=useLiveFocusItems()
  const {language,t}=useLanguage()
  const [filter,setFilter]=useState('All')
  const priorityItems=useMemo(()=>items.filter(item=>!item.id.startsWith('distribution-')),[items])
  const visible=useMemo(()=>priorityItems.filter(item=>filter==='All'||item.priority===filter.toLowerCase()),[priorityItems,filter])
  const subtitle=(text:string)=>text.split(/(\d+)/).map((part,index)=>/^\d+$/.test(part)?<b className="focus-page__count" key={`${part}-${index}`}>{part}</b>:part)
  return <section className="focus-page">
    {error && <p role="status">{language === 'ar' ? 'تعذر تحديث بعض التنبيهات. المعروض قد يكون غير مكتمل أو غير محدّث؛ ستتم إعادة المحاولة تلقائيًا.' : 'Some reminders could not refresh. Results may be incomplete or out of date; retrying automatically.'}</p>}
    <header><PageNavigation/><div className="focus-page__identity"><span><ListTodo size={21}/></span><div><p>{t('Personal attention center')}</p><h1>{t('Focus')}</h1><small>{t('Real upcoming obligations.')}</small></div></div></header>
    <div className="focus-page__metrics"><article><span>{t('Needs attention')}</span><strong>{priorityItems.length}</strong><small>{t('Live items')}</small></article><article><span>{t('Credit card reminders')}</span><strong>{priorityItems.filter(item=>item.id.startsWith('card-')).length}</strong><small>{t('Live items')}</small></article><article><span>{t('High priority')}</span><strong>{priorityItems.filter(item=>item.priority==='high').length}</strong><small>{t('Act soon')}</small></article></div>
    <section className="focus-page__panel"><div className="focus-page__toolbar"><div><h2>{t('All focus items')}</h2><p>{t('Ordered from your posted data')}</p></div><nav>{['All','High','Medium','Low'].map(value=><button className={filter===value?'is-active':''} type="button" onClick={()=>setFilter(value)} key={value}>{t(value)}</button>)}</nav></div><div className="focus-page__list-head"><span aria-hidden="true"/><span>{t('Alert')}</span><span>{t('Priority')}</span><span>{t('Amount')}</span><span>{t('Action')}</span></div><div className="focus-page__list">{visible.map(item=><article key={item.id}><i className={`is-${item.priority}`}>{item.icon}</i><div><strong>{item.title}</strong><small>{item.bankName?<span className="focus-page__bank-icon"><BankIdentity bank={item.bankName}>{null}</BankIdentity></span>:<CalendarClock size={13}/>} {subtitle(item.subtitle)}</small></div><em className={`is-${item.priority}`}>{t(item.priority)}</em><b>{item.amount==null?t('Review'):formatDisplayNumber(item.amount,{minimumFractionDigits:2,maximumFractionDigits:2},language)}</b><div className="focus-page__actions"><button type="button" onClick={()=>navigate(item.route)}><CheckCircle2 size={15}/>{t('Open')}</button></div></article>)}{!loading&&!error&&!visible.length&&<div className="focus-page__empty"><CheckCircle2 size={22}/><strong>{t('You’re all caught up')}</strong><span>{t('No live items match this filter.')}</span></div>}</div></section>
  </section>
}
