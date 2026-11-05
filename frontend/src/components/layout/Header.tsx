import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import {
  Bell,
  CircleUserRound,
  Languages,
  Menu,
  Search,
  Wallet,
  X,
  FileWarning,
  CheckCircle2,
  CreditCard,
  History,
  Trash2,
} from 'lucide-react'
import { useNavigate } from 'react-router-dom'

import ThemeToggle from './ThemeToggle'
import CurrencyMark from '../ui/CurrencyMark'
import { useCurrency } from '../../context/CurrencyContext'
import { getPendingImportBatches } from '../../services/importReviewService'
import { useLanguage } from '../../context/LanguageContext'
import FormattedMoney from '../ui/FormattedMoney'
import { formatDate } from '../../utils/dateFormat'
import { addRecentSearch, clearRecentSearches, getRecentSearches } from '../../utils/searchHistory'
import { getFinancialSummary, type FinancialActivity } from '../../services/accountingService'
import { useLiveFocusItems } from '../../hooks/useLiveFocusItems'

import './Header.css'
import './CurrencyMenu.css'

type Props = {
  collapsed: boolean
  onToggleSidebar: () => void
}

const notificationStorageKey='wealthos-read-event-notifications'
const announcedNotificationStorageKey='wealthos-announced-event-notifications-v10'
const storedIds=(key:string)=>{try{return new Set<string>(JSON.parse(localStorage.getItem(key)??'[]') as string[])}catch{return new Set<string>()}}
const readNotificationIds=()=>storedIds(notificationStorageKey)

export default function Header({
  onToggleSidebar,
}: Props) {
  const { currency, enabledCurrencies, selectCurrency, formatMoney } = useCurrency()
  const { language, toggleLanguage, t } = useLanguage()
  const navigate = useNavigate()
  const { items: focusItems } = useLiveFocusItems()
  const attentionNotifications = useMemo(
    ()=>focusItems.filter((item) => item.id.startsWith('card-') || item.id.startsWith('distribution-')),
    [focusItems],
  )
  const [readIds,setReadIds]=useState<Set<string>>(readNotificationIds)
  const unreadAttentionNotifications=useMemo(()=>attentionNotifications.filter(item=>!readIds.has(item.id)),[attentionNotifications,readIds])
  const unreadCardNotifications=useMemo(()=>unreadAttentionNotifications.filter(item=>item.id.startsWith('card-')),[unreadAttentionNotifications])
  const unreadDistributionNotifications=useMemo(()=>unreadAttentionNotifications.filter(item=>item.id.startsWith('distribution-')),[unreadAttentionNotifications])
  const [currencyOpen, setCurrencyOpen] = useState(false)
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [pendingReviewCount, setPendingReviewCount] = useState(0)
  const [dueReminderCount, setDueReminderCount] = useState(0)
  const [paymentEvents,setPaymentEvents]=useState<FinancialActivity[]>([])
  const [searchOpen, setSearchOpen] =
    useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [recentSearches,setRecentSearches]=useState<string[]>(getRecentSearches)

  function runSearch(value: string) {
    const query = value.trim()
    if (!query) return
    setRecentSearches(addRecentSearch(query))
    setSearchOpen(false)
    setSearchQuery('')
    navigate(`/search?q=${encodeURIComponent(query)}`)
  }

  const searchRef =
    useRef<HTMLDivElement>(null)
  const currencyRef = useRef<HTMLDivElement>(null)
  const notificationsRef = useRef<HTMLDivElement>(null)
  const audioUnlockedRef=useRef(false)

  useEffect(() => {
    getPendingImportBatches().then((batches) => {
      setPendingReviewCount(batches.reduce((total, batch) => total + batch.operations.filter((item) => item.status === 'PENDING').length, 0))
      setDueReminderCount(batches.filter((batch) => batch.reminder_due).length)
    }).catch(() => undefined)
    getFinancialSummary().then(summary=>{const read=readNotificationIds();setPaymentEvents(summary.recent_activity.filter(item=>item.related_reference?.startsWith('credit-card-payment:')&&!read.has(String(item.id))))}).catch(()=>setPaymentEvents([]))
  }, [notificationsOpen])

  const notificationCount=pendingReviewCount+paymentEvents.length+unreadAttentionNotifications.length
  const markCardNotificationRead=(id:string)=>{setReadIds(current=>{const next=new Set(current);next.add(id);localStorage.setItem(notificationStorageKey,JSON.stringify([...next].slice(-200)));return next})}
  const openPaymentEvent=(item:FinancialActivity)=>{const read=readNotificationIds();read.add(String(item.id));localStorage.setItem(notificationStorageKey,JSON.stringify([...read].slice(-100)));setPaymentEvents(current=>current.filter(event=>event.id!==item.id));setNotificationsOpen(false);navigate('/activity')}

  useEffect(()=>{
    const syncReadNotifications=()=>setReadIds(readNotificationIds())
    window.addEventListener('wealthos-notifications-read',syncReadNotifications)
    return()=>window.removeEventListener('wealthos-notifications-read',syncReadNotifications)
  },[])

  useEffect(()=>{
    const announced=storedIds(announcedNotificationStorageKey)
    const fresh=unreadAttentionNotifications.filter(item=>!announced.has(item.id))
    if(!fresh.length)return
    const AudioContextClass=window.AudioContext||(window as typeof window&{webkitAudioContext:typeof AudioContext}).webkitAudioContext
    let played=false
    const play=async()=>{
      if(played)return
      try{
        audioUnlockedRef.current=true
        const context=new AudioContextClass()
        await context.resume()
        if(context.state!=='running')return
        const gain=context.createGain(),first=context.createOscillator(),second=context.createOscillator()
        first.connect(gain);second.connect(gain);gain.connect(context.destination)
        first.frequency.value=784;second.frequency.value=1046.5
        const now=context.currentTime
        gain.gain.setValueAtTime(.22,now);gain.gain.exponentialRampToValueAtTime(.001,now+.75)
        first.start(now);second.start(now+.08);first.stop(now+.68);second.stop(now+.75);played=true
        second.onended=()=>void context.close()
        fresh.forEach(item=>announced.add(item.id));localStorage.setItem(announcedNotificationStorageKey,JSON.stringify([...announced].slice(-200)))
        window.removeEventListener('pointerdown',play);window.removeEventListener('keydown',play)
      }catch{return}
    }
    if(audioUnlockedRef.current)void play()
    window.addEventListener('pointerdown',play,{once:true});window.addEventListener('keydown',play,{once:true})
    return()=>{window.removeEventListener('pointerdown',play);window.removeEventListener('keydown',play)}
  },[unreadAttentionNotifications])

  useEffect(() => {
    function handleMouseDown(
      event: MouseEvent,
    ) {
      if (
        searchRef.current &&
        !searchRef.current.contains(
          event.target as Node,
        )
      ) {
        setSearchOpen(false)
      }
      if (currencyRef.current && !currencyRef.current.contains(event.target as Node)) {
        setCurrencyOpen(false)
      }
      if (notificationsRef.current && !notificationsRef.current.contains(event.target as Node)) {
        setNotificationsOpen(false)
      }
    }

    function handleKeyDown(
      event: KeyboardEvent,
    ) {
      if (event.key === 'Escape') {
        setSearchOpen(false)
        setNotificationsOpen(false)
      }
    }

    document.addEventListener(
      'mousedown',
      handleMouseDown,
    )

    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    return () => {
      document.removeEventListener(
        'mousedown',
        handleMouseDown,
      )

      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [])

  return (
    <header className="header">
      <div className="header__top">
        <div className="header__leading">
          <button
            aria-label={t('Toggle navigation')}
            className="header__module-button"
            type="button"
            onClick={onToggleSidebar}
          >
            <Menu size={18} />
          </button>

          <div className={`header__search-control${searchOpen?' is-open':''}`} ref={searchRef}>
            {!searchOpen?<button className="header__search-trigger" type="button" onClick={() => {setRecentSearches(getRecentSearches());setSearchOpen(true)}}><Search size={18}/><span>{t('Search WealthOS')}</span></button>:<div className="header__search-inline"><Search size={18}/><input autoFocus placeholder={t('Search WealthOS...')} type="text" value={searchQuery} onChange={event=>setSearchQuery(event.target.value)} onKeyDown={event=>{if(event.key==='Enter')runSearch(searchQuery)}}/><button type="button" aria-label={t('Close')} onClick={()=>{setSearchOpen(false);setSearchQuery('')}}><X size={17}/></button></div>}
            {searchOpen&&recentSearches.length>0&&<div className="header__search-dropdown header__recent-searches"><header><h4>{t('Recent Searches')}</h4><button type="button" onClick={()=>{clearRecentSearches();setRecentSearches([])}}><Trash2 size={13}/>{t('Clear')}</button></header>{recentSearches.map(item=><button type="button" onClick={()=>runSearch(item)} key={item}><History size={15}/><span>{item}</span></button>)}</div>}
          </div>
        </div>

        <div className="header__actions">
          <ThemeToggle />

          <button
            className="header__action-button"
            type="button"
            onClick={toggleLanguage}
            title={t(language === 'en' ? 'Switch to Arabic' : 'Switch to English')}
            aria-label={t(language === 'en' ? 'Switch to Arabic' : 'Switch to English')}
          >
            <Languages size={18} />
            <span>{language === 'en' ? 'EN' : 'AR'}</span>
          </button>

          <div className="header__currency-control" ref={currencyRef}>
            <button className="header__action-button" type="button" onClick={() => setCurrencyOpen((value) => !value)} aria-expanded={currencyOpen}>
              <Wallet size={18} /><span>{currency}</span>
            </button>
            {currencyOpen && <div className="header__currency-menu"><small>{t('Display Currency')}</small>{enabledCurrencies.map((code) => <button className={currency === code ? 'is-active' : ''} type="button" onClick={() => { selectCurrency(code); setCurrencyOpen(false) }} key={code}><span><CurrencyMark currency={code}/>{code}</span>{currency === code && '✓'}</button>)}<button type="button" onClick={()=>{setCurrencyOpen(false);navigate('/settings/currencies')}}>{t('Manage Currencies')}</button></div>}
          </div>

          <div className="header__notifications" ref={notificationsRef}>
            <button className="header__action-button header__notification-trigger" type="button" aria-label={t('Notifications')} aria-expanded={notificationsOpen} onClick={() => setNotificationsOpen((value) => !value)}><Bell size={18} />{notificationCount>0&&<span className="header__notification-badge">{notificationCount}</span>}</button>
            {notificationsOpen && <section className="notification-menu" dir={language === 'ar' ? 'rtl' : 'ltr'}>
              <header><div className="notification-menu__heading"><i><Bell size={17}/></i><div><strong>{t('Notifications')}</strong><span>{notificationCount} {t('Need Attention')}</span></div></div><button type="button" aria-label={t('Close')} title={t('Close')} onClick={()=>setNotificationsOpen(false)}><X size={16}/></button></header>
              {paymentEvents.length>0&&<div className="notification-menu__group"><p>{t('Completed activity')}</p>{paymentEvents.map(item=><button type="button" key={item.id} onClick={()=>openPaymentEvent(item)}><i className="is-success"><CheckCircle2 size={16}/></i><span><strong>{t('Credit card payment recorded successfully')}</strong><small>{formatDate(item.transaction_date)} · <FormattedMoney value={formatMoney(Math.abs(item.cash_change))}/></small></span><em>{t('View')}</em></button>)}</div>}
              {unreadDistributionNotifications.length>0&&<div className="notification-menu__group"><p>{language==='ar'?'توزيعات الاستثمارات':'Investment distributions'}</p>{unreadDistributionNotifications.map(item=><div className="notification-menu__item" key={item.id}><button type="button" onClick={()=>{setNotificationsOpen(false);markCardNotificationRead(item.id);navigate(item.route)}}><i className={item.priority==='high'?'is-warning':''}>{item.icon}</i><span><strong>{item.title}</strong><small>{item.subtitle}{item.amount!=null?` · ${formatMoney(item.amount,item.amountCurrency)}`:''}</small></span></button><button className="notification-menu__read" type="button" onClick={()=>markCardNotificationRead(item.id)}>{t('Mark as read')}</button></div>)}</div>}
              {unreadCardNotifications.length>0&&<div className="notification-menu__group"><p>{t('Credit card reminders')}</p>{unreadCardNotifications.map(item=><div className="notification-menu__item" key={item.id}><button type="button" onClick={()=>{setNotificationsOpen(false);navigate(item.route)}}><i className={item.priority==='high'?'is-warning':''}><CreditCard size={16}/></i><span><strong>{item.title}</strong><small>{item.subtitle}{item.paymentStatus?` · ${t(item.paymentStatus==='paid'?'Paid':'Unpaid')}`:''}</small></span></button><button className="notification-menu__read" type="button" onClick={()=>markCardNotificationRead(item.id)}>{t('Mark as read')}</button></div>)}</div>}
              {pendingReviewCount>0&&<div className="notification-menu__group"><p>{t(dueReminderCount>0?'Reminder due':'Needs attention')}</p><button type="button" onClick={() => { setNotificationsOpen(false); navigate('/accounting/review-queue') }}><i className="is-warning"><FileWarning size={16}/></i><span><strong>{pendingReviewCount} {t('imported operations need review')}</strong><small>{dueReminderCount>0?`${dueReminderCount} ${t('review reminders due')}`:t('Saved safely for later review')}</small></span><em>{t('Review')}</em></button></div>}
              {notificationCount===0&&<div className="notification-menu__empty"><i><CheckCircle2 size={21}/></i><div><strong>{t('All Clear')}</strong><span>{t('No pending notifications.')}</span></div></div>}
            </section>}
          </div>

          <button
            className="header__action-button header__profile"
            type="button"
            onClick={()=>navigate('/settings/profile')}
            aria-label={t('Open Profile Settings')}
          >
            <CircleUserRound size={20} />
          </button>
        </div>
      </div>

    </header>
  )
}
