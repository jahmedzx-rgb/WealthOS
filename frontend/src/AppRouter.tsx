import {
  BrowserRouter,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { lazy, Suspense, useEffect, useLayoutEffect, useState } from 'react'

import AppLayout from './components/layout/AppLayout'

import BetaProfileInitializer from './components/BetaProfileInitializer'
import BootstrapGate from './components/BootstrapGate'
import { useLanguage } from './context/LanguageContext'
import { syncDistributionAnnouncements } from './services/notificationService'

const OperationWorkspacePage=lazy(()=>import('./pages/OperationWorkspacePage'))
const OperationsCatalogPage=lazy(()=>import('./pages/OperationsCatalogPage'))
const PortfolioDashboardPage=lazy(()=>import('./pages/PortfolioDashboardPage'))
const PositionDetailsPage=lazy(()=>import('./pages/PositionDetailsPage'))
const ModulePage=lazy(()=>import('./pages/ModulePage'))
const ReportingPage=lazy(()=>import('./pages/ReportingPage'))
const CurrencySettingsPage=lazy(()=>import('./pages/CurrencySettingsPage'))
const AccountingPage=lazy(()=>import('./pages/AccountingRoutePage'))
const AccountingToolPage=lazy(()=>import('./pages/AccountingToolPage'))
const ReviewQueuePage=lazy(()=>import('./pages/ReviewQueuePage'))
const PositionsPage=lazy(()=>import('./pages/PositionsPage'))
const FocusPage=lazy(()=>import('./pages/FocusPage'))
const RecentActivityPage=lazy(()=>import('./pages/RecentActivityPage'))
const JournalEntryDetailsPage=lazy(()=>import('./pages/JournalEntryDetailsPage'))
const SettingsPage=lazy(()=>import('./pages/SettingsPage'))
const ProfileSettingsPage=lazy(()=>import('./pages/ProfileSettingsPage'))
const SecuritySettingsPage=lazy(()=>import('./pages/SecuritySettingsPage'))
const BrokersPage=lazy(()=>import('./pages/BrokersPage'))
const DataAccountSettingsPage=lazy(()=>import('./pages/DataAccountSettingsPage'))
const SearchResultsPage=lazy(()=>import('./pages/SearchResultsPage'))
const LibraryPage=lazy(()=>import('./pages/LibraryPage'))
const SystemIndexPage=lazy(()=>import('./pages/SystemIndexPage'))
const DepositsPage=lazy(()=>import('./pages/DepositsPage'))
const CashPage=lazy(()=>import('./pages/CashPage'))
const AlternativeInvestmentsPage=lazy(()=>import('./pages/AlternativeInvestmentsPage'))
const FinancialPlatformsPage=lazy(()=>import('./pages/InvestmentProductPages').then(module=>({default:module.FinancialPlatformsPage})))
const SavingCirclesPage=lazy(()=>import('./pages/InvestmentProductPages').then(module=>({default:module.SavingCirclesPage})))
const PropertyPages=lazy(()=>import('./pages/PropertyPages'))
const InvestmentCashFlowsPage=lazy(()=>import('./pages/InvestmentCashFlowsPage'))
const MonthClosePage=lazy(()=>import('./pages/MonthClosePage'))
const ReconciliationView=lazy(()=>import('./pages/ReconciliationView'))
const LoanDetailsPage=lazy(()=>import('./pages/LoanDetailsPage'))
const LoansAccountingPage=lazy(()=>import('./pages/LoansAccountingPage'))
const DigitalWalletsPage=lazy(()=>import('./pages/DigitalWalletsPage'))
const CreditCardPaymentHistoryPage=lazy(()=>import('./pages/CreditCardPaymentHistoryPage'))
const AnalyticsPage=lazy(()=>import('./pages/AnalyticsPage'))

function ScrollToTop() {
  const { pathname } = useLocation()

  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: 'instant' })
  }, [pathname])

  return null
}

const PAGE_TITLES: Array<[RegExp, string]> = [
  [/^\/$/, 'Home'],
  [/^\/analytics\/?$/, 'Analytics'],
  [/^\/operations\/[^/]+\/?$/, 'Operation'],
  [/^\/operations\/?$/, 'Operations'],
  [/^\/portfolios\/[^/]+\/positions\/[^/]+\/?$/, 'Position Details'],
  [/^\/investing\/positions\/?$/, 'Stocks'],
  [/^\/investing\/cash-flows\/?$/, 'Investment Cash Flows'],
  [/^\/investing\/alternative-investments\/?$/, 'Alternative Investments'],
  [/^\/investing\/cash\/?$/, 'Cash'],
  [/^\/investing\/brokers\/?$/, 'Brokers'],
  [/^\/investing\/platforms\/?$/, 'Alt. Investment Platforms'],
  [/^\/investing\/?$/, 'Investing'],
  [/^\/(?:savings|investing\/saving-circles)\/?$/, 'Savings'],
  [/^\/(?:savings\/deposits|investing\/deposits)\/?$/, 'Deposits'],
  [/^\/focus\/?$/, 'Priorities'],
  [/^\/activity\/[^/]+\/?$/, 'Activity Details'],
  [/^\/activity\/?$/, 'Recent Activity'],
  [/^\/search\/?$/, 'Search'],
  [/^\/library\/?$/, 'Library'],
  [/^\/index\/?$/, 'Index'],
  [/^\/bank-accounts\/?$/, 'Bank Accounts'],
  [/^\/e-wallets\/new\/?$/, 'New E-Wallet'],
  [/^\/e-wallets\/?$/, 'E-Wallets'],
  [/^\/credit-cards\/[^/]+\/payments\/?$/, 'Payment History'],
  [/^\/credit-cards\/?$/, 'Credit Cards'],
  [/^\/properties\/income\/?$/, 'Property Income'],
  [/^\/properties\/expenses\/?$/, 'Property Expenses'],
  [/^\/properties\/?$/, 'Properties'],
  [/^\/accounting\/review-queue\/?$/, 'Review Queue'],
  [/^\/accounting\/ledger\/?$/, 'General Ledger'],
  [/^\/accounting\/journals\/?$/, 'Journal Entries'],
  [/^\/accounting\/reconciliation\/?$/, 'Reconciliation'],
  [/^\/accounting\/month-close\/?$/, 'Monthly Snapshots'],
  [/^\/accounting\/loans\/[^/]+\/?$/, 'Loan Details'],
  [/^\/accounting\/loans\/?$/, 'Loans'],
  [/^\/accounting\/?$/, 'Accounting'],
  [/^\/reporting\/?$/, 'Reporting'],
  [/^\/settings\/profile\/?$/, 'Profile'],
  [/^\/settings\/security\/?$/, 'Security'],
  [/^\/settings\/currencies\/?$/, 'Currencies'],
  [/^\/settings\/data-account\/?$/, 'Data & Account'],
  [/^\/settings\/?$/, 'Settings'],
]

function DocumentTitle() {
  const { pathname } = useLocation()

  useEffect(() => {
    const page = PAGE_TITLES.find(([pattern]) => pattern.test(pathname))?.[1] ?? 'Home'
    document.title = `WealthOS | ${page}`
  }, [pathname])

  return null
}

function RouteLoading() {
  const { direction } = useLanguage()
  const [slow, setSlow] = useState(false)
  useEffect(() => {
    const timer = window.setTimeout(() => setSlow(true), 12_000)
    return () => window.clearTimeout(timer)
  }, [])
  return <div className="app-route-loading">
    {slow ? direction === 'rtl' ? 'تأخر تحميل الصفحة عن المعتاد.' : 'The page is taking longer than expected.' : direction === 'rtl' ? 'جارٍ تحميل WealthOS…' : 'Loading WealthOS…'}
    {slow && <button type="button" onClick={() => window.location.reload()} style={{ display: 'block', margin: '12px auto' }}>{direction === 'rtl' ? 'إعادة تحميل الصفحة' : 'Reload page'}</button>}
  </div>
}

export default function AppRouter() {
  useEffect(() => {
    const timer = window.setTimeout(() => {
      ;['alinma-capital','alkhabeer-capital','alkhabeer-global','rajhi-capital','snb-capital'].forEach(name=>{const image=new Image();image.src=`/brokers/${name}.png?v=local-20260924`})
    }, 1_500)
    return () => window.clearTimeout(timer)
  }, [])
  useEffect(() => {
    const key = 'wealthos:distribution-sync-next-at:v2'
    const now = Date.now()
    try {
      if (Number(localStorage.getItem(key) ?? 0) > now) return
    } catch {
      // A blocked local cache must not prevent app startup.
    }
    let started = false
    const readyAt = Date.now() + 45_000
    const startSync = () => {
      if (started || Date.now() < readyAt || document.visibilityState === 'hidden') return
      started = true
      window.clearTimeout(timer)
      document.removeEventListener('visibilitychange', startSync)
      try { localStorage.setItem(key, String(Date.now() + 6 * 60 * 60 * 1000)) } catch { /* ignore cache errors */ }
      void syncDistributionAnnouncements().then(() => {
        try { localStorage.setItem(key, String(Date.now() + 24 * 60 * 60 * 1000)) } catch { /* ignore cache errors */ }
      }).catch(() => undefined)
    }
    const timer = window.setTimeout(startSync, 45_000)
    document.addEventListener('visibilitychange', startSync)
    return () => { window.clearTimeout(timer); document.removeEventListener('visibilitychange', startSync) }
  }, [])
  return (
    <BrowserRouter>
      <ScrollToTop />
      <DocumentTitle />
      <BootstrapGate><BetaProfileInitializer />
      <Suspense fallback={<RouteLoading />}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={<PortfolioDashboardPage />}
          />
          <Route path="/analytics" element={<AnalyticsPage />} />

          <Route
            path="/operations/:operation"
            element={<OperationWorkspacePage />}
          />

          <Route
            path="/operations"
            element={<OperationsCatalogPage />}
          />

          <Route
            path="/portfolios/:portfolioId/positions/:securityId"
            element={<PositionDetailsPage />}
          />
          <Route path="/investing" element={<ModulePage module="investing" />} />
          <Route path="/investing/positions" element={<PositionsPage />} />
          <Route path="/investing/deposits" element={<DepositsPage />} />
          <Route path="/investing/cash-flows" element={<InvestmentCashFlowsPage />} />
          <Route path="/investing/cash" element={<CashPage />} />
          <Route path="/savings/deposits" element={<DepositsPage />} />
          <Route path="/investing/brokers" element={<BrokersPage />} />
          <Route path="/investing/platforms" element={<FinancialPlatformsPage />} />
          <Route path="/investing/alternative-investments" element={<AlternativeInvestmentsPage />} />
          <Route path="/savings" element={<SavingCirclesPage />} />
          <Route path="/investing/saving-circles" element={<SavingCirclesPage />} />
          <Route path="/focus" element={<FocusPage />} />
          <Route path="/activity" element={<RecentActivityPage />} />
          <Route path="/activity/:entryId" element={<JournalEntryDetailsPage />} />
          <Route path="/search" element={<SearchResultsPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/index" element={<SystemIndexPage />} />
          <Route path="/bank-accounts" element={<ModulePage module="banking" />} />
          <Route path="/e-wallets" element={<DigitalWalletsPage />} />
          <Route path="/e-wallets/new" element={<DigitalWalletsPage createMode />} />
          <Route path="/credit-cards" element={<ModulePage module="cards" />} />
          <Route path="/credit-cards/:cardId/payments" element={<CreditCardPaymentHistoryPage />} />
          <Route path="/properties" element={<PropertyPages view="summary" />} />
          <Route path="/properties/income" element={<PropertyPages view="income" />} />
          <Route path="/properties/expenses" element={<PropertyPages view="expenses" />} />
          <Route path="/accounting" element={<AccountingPage />} />
          <Route path="/accounting/ledger" element={<AccountingToolPage tool="ledger" />} />
          <Route path="/accounting/journals" element={<AccountingToolPage tool="journals" />} />
          <Route path="/accounting/reconciliation" element={<ReconciliationView standalone />} />
          <Route path="/accounting/review-queue" element={<ReviewQueuePage />} />
          <Route path="/accounting/month-close" element={<MonthClosePage />} />
          <Route path="/accounting/loans/:loanId" element={<LoanDetailsPage />} />
          <Route path="/accounting/loans" element={<LoansAccountingPage />} />
          <Route path="/reporting" element={<ReportingPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/profile" element={<ProfileSettingsPage />} />
          <Route path="/settings/security" element={<SecuritySettingsPage />} />
          <Route path="/settings/currencies" element={<CurrencySettingsPage />} />
          <Route path="/settings/data-account" element={<DataAccountSettingsPage />} />
        </Route>
      </Routes>
      </Suspense>
      </BootstrapGate>
    </BrowserRouter>
  )
}
