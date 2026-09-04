import { NavLink, useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'

import {
  Building2,
  ChartColumn,
  ChartCandlestick,
  CreditCard,
  BookOpen,
  ChevronDown,
  FileText,
  Landmark,
  LayoutDashboard,
  Settings,
  ListChecks,
  RefreshCcw,
  Inbox,
  Moon,
  Sun,
  LibraryBig,
  ListTree,
  Sprout,
  WalletCards,
  Layers3,
  CircleDollarSign,
  ReceiptText,
  Coins,
  CalendarCheck2,
} from 'lucide-react'

import { APP } from '../../config/app'
import { loadUserProfile } from '../../pages/userProfile'
import { useLanguage } from '../../context/LanguageContext'
import { getPendingImportBatches } from '../../services/importReviewService'
import wealthosIcon from '../../../../assets/branding/wealthos-app-icon.svg'

import './Sidebar.css'
import './SidebarAccounting.css'
import './SidebarReviewQueue.css'

type Props = {
  collapsed: boolean
}

const navigationItems = [
  {
    label: 'Home',
    icon: LayoutDashboard,
    path: '/',
  },
  {
    label: 'Investing',
    icon: ChartCandlestick,
    path: '/investing',
  },
  {
    label: 'Bank Accounts',
    icon: Landmark,
    path: '/bank-accounts',
  },
  {
    label: 'Credit Cards',
    icon: CreditCard,
    path: '/credit-cards',
  },
  {
    label: 'Properties',
    icon: Building2,
    path: '/properties',
  },
  {
    label: 'Accounting',
    icon: FileText,
    path: '/accounting',
  },
  {
    label: 'Reporting',
    icon: ChartColumn,
    path: '/reporting',
  },
  {
    label: 'Library',
    icon: LibraryBig,
    path: '/library',
  },
  {
    label: 'Index',
    icon: ListTree,
    path: '/index',
  },
  {
    label: 'Settings',
    icon: Settings,
    path: '/settings',
  },
]

const navigationSections = [
  { label: 'Workspace', items: navigationItems.slice(0, 1) },
  { label: 'Wealth', items: navigationItems.slice(1, 5) },
  { label: 'Intelligence', items: navigationItems.slice(5, 8) },
  { label: 'System', items: navigationItems.slice(8) },
]

export default function Sidebar({
  collapsed,
}: Props) {
  const location = useLocation()
  const { language, t } = useLanguage()
  const investingOpen = location.pathname.startsWith('/investing') || location.pathname.startsWith('/portfolios/')
  const accountingOpen = location.pathname.startsWith('/accounting')
  const propertiesOpen = location.pathname.startsWith('/properties')
  const [investingExpanded, setInvestingExpanded] = useState(investingOpen)
  const [accountingExpanded, setAccountingExpanded] = useState(accountingOpen)
  const [propertiesExpanded, setPropertiesExpanded] = useState(propertiesOpen)
  const investingMenuOpen = investingExpanded
  const [currentTime, setCurrentTime] = useState(() => new Date())
  const [profile, setProfile] = useState(loadUserProfile)
  const [pendingReviewCount, setPendingReviewCount] = useState(0)
  useEffect(() => {
    const timer = window.setInterval(() => setCurrentTime(new Date()), 60_000)
    const updateProfile = () => setProfile(loadUserProfile())
    window.addEventListener('wealthos-profile-updated', updateProfile)
    window.addEventListener('storage', updateProfile)
    return () => { window.clearInterval(timer); window.removeEventListener('wealthos-profile-updated', updateProfile); window.removeEventListener('storage', updateProfile) }
  }, [])
  useEffect(() => {
    getPendingImportBatches()
      .then((batches) => setPendingReviewCount(batches.reduce((total, batch) => total + batch.operations.filter((item) => item.status === 'PENDING').length, 0)))
      .catch(() => setPendingReviewCount(0))
  }, [location.pathname])
  const currentHour = currentTime.getHours()
  const isDaytime = currentHour >= 5 && currentHour < 18
  const greeting = t(currentHour < 12 && currentHour >= 5 ? 'Good Morning' : currentHour < 17 && currentHour >= 12 ? 'Good Afternoon' : 'Good Evening')
  const greetingNote = t(currentHour < 12 && currentHour >= 5 ? 'Wishing You A Productive Morning' : currentHour < 17 && currentHour >= 12 ? 'Wishing You A Successful Day' : 'A Calm Financial Evening')
  const GreetingIcon = isDaytime ? Sun : Moon

  return (
    <aside
      className={`sidebar ${
        collapsed
          ? 'sidebar--collapsed'
          : ''
      }`}
    >
      <div className="sidebar__brand">
        <span className="sidebar__brand-mark"><img src={wealthosIcon} alt="" aria-hidden="true" /></span>
        {!collapsed && (
          <span className="sidebar__brand-lockup">
            <strong className="sidebar__brand-name">{APP.name}</strong>
            <small>{t('Private Wealth')}</small>
          </span>
        )}
      </div>

      <div className="sidebar__greeting" dir={language==='ar'?'rtl':'ltr'} title={`${greeting} ${profile.fullName}`}>
        <span className={isDaytime ? 'is-sun' : 'is-moon'}><GreetingIcon size={18}/></span>
        {!collapsed&&<div><strong>{greeting},{' '}{profile.fullName}</strong><small>{greetingNote}</small></div>}
      </div>

      <nav className="sidebar__navigation">
        {navigationSections.map((section)=><section className="sidebar__nav-section" key={section.label}>
          {!collapsed&&<p>{t(section.label)}</p>}
          <div>{section.items.map((item) => {
          const Icon = item.icon

          if (item.label === 'Investing') return <div className="sidebar__group" key={item.label}>
            <button className={`sidebar__group-toggle${investingOpen?' active':''}`} type="button" onClick={()=>setInvestingExpanded((expanded)=>!expanded)} aria-expanded={investingMenuOpen}><Icon size={18}/>{!collapsed&&<><span>{t('Investing')}</span><ChevronDown className={`sidebar__chevron ${investingMenuOpen?'is-open':''}`} size={14}/></>}</button>
            {investingMenuOpen&&!collapsed&&<div className="sidebar__submenu"><NavLink to="/investing" end>{t('Executive Summary')}</NavLink><NavLink to="/investing/positions"><ChartCandlestick size={14}/>{t('Stocks')}</NavLink><NavLink to="/investing/deposits"><Sprout size={14}/>{t('Deposits')}</NavLink><NavLink to="/investing/cash-flows"><Coins size={14}/>{t('Investment Cash Flows')}</NavLink><NavLink to="/investing/alternative-investments"><Layers3 size={14}/>{t('Alternative Investments')}</NavLink><NavLink to="/investing/saving-circles"><CircleDollarSign size={14}/>{t('Saving Circles')}</NavLink><NavLink to="/investing/cash"><WalletCards size={14}/>{t('Cash')}</NavLink><NavLink to="/properties"><Building2 size={14}/>{t('Properties')}</NavLink><NavLink to="/investing/brokers"><Building2 size={14}/>{t('Brokers')}</NavLink><NavLink to="/investing/platforms"><Building2 size={14}/>{t('Financial Platforms')}</NavLink></div>}
          </div>

          if (item.label === 'Accounting') return <div className="sidebar__group" key={item.label}>
            <button className={`sidebar__group-toggle${accountingOpen?' active':''}`} type="button" onClick={()=>setAccountingExpanded((expanded)=>!expanded)} aria-expanded={accountingExpanded}><Icon size={18}/>{!collapsed&&<><span>{t('Accounting')}</span><ChevronDown className={`sidebar__chevron ${accountingExpanded?'is-open':''}`} size={14}/></>}</button>
            {accountingExpanded&&!collapsed&&<div className="sidebar__submenu"><NavLink to="/accounting" end>{t('Executive Summary')}</NavLink><NavLink to="/accounting/review-queue"><Inbox size={14}/>{t('Review Queue')} {pendingReviewCount>0&&<em>{pendingReviewCount}</em>}</NavLink><NavLink to="/accounting/ledger"><BookOpen size={14}/>{t('General Ledger')}</NavLink><NavLink to="/accounting/journals"><ListChecks size={14}/>{t('Journal Entries')}</NavLink><NavLink to="/accounting/reconciliation"><RefreshCcw size={14}/>{t('Reconciliation')}</NavLink><NavLink to="/accounting/month-close"><CalendarCheck2 size={14}/>{t('Monthly Snapshots')}</NavLink></div>}
          </div>

          if (item.label === 'Properties') return <div className="sidebar__group" key={item.label}>
            <button className={`sidebar__group-toggle${propertiesOpen?' active':''}`} type="button" onClick={()=>setPropertiesExpanded((expanded)=>!expanded)} aria-expanded={propertiesExpanded}><Icon size={18}/>{!collapsed&&<><span>{t('Properties')}</span><ChevronDown className={`sidebar__chevron ${propertiesExpanded?'is-open':''}`} size={14}/></>}</button>
            {propertiesExpanded&&!collapsed&&<div className="sidebar__submenu"><NavLink to="/properties" end>{t('Executive Summary')}</NavLink><NavLink to="/properties/income"><ChartColumn size={14}/>{t('Property Income')}</NavLink><NavLink to="/properties/expenses"><ReceiptText size={14}/>{t('Property Expenses')}</NavLink></div>}
          </div>

          return (
            <NavLink
              key={item.label}
              to={item.path}
              end={item.path === '/'}
              className={({ isActive }) => isActive ? 'active' : ''}
            >
              <Icon size={18} />

              {!collapsed && (
                <span>{t(item.label)}</span>
              )}
            </NavLink>
          )
        })}</div></section>)}
      </nav>
    </aside>
  )
}
