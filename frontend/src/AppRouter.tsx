import {
  BrowserRouter,
  Route,
  Routes,
} from 'react-router-dom'
import { lazy, Suspense } from 'react'

import AppLayout from './components/layout/AppLayout'

import BetaProfileInitializer from './components/BetaProfileInitializer'
import SetupGate from './components/SetupGate'

const OperationWorkspacePage=lazy(()=>import('./pages/OperationWorkspacePage'))
const OperationsCatalogPage=lazy(()=>import('./pages/OperationsCatalogPage'))
const PortfolioDashboardPage=lazy(()=>import('./pages/PortfolioDashboardPage'))
const PositionDetailsPage=lazy(()=>import('./pages/PositionDetailsPage'))
const ModulePage=lazy(()=>import('./pages/ModulePage'))
const ReportingPage=lazy(()=>import('./pages/ReportingPage'))
const CurrencySettingsPage=lazy(()=>import('./pages/CurrencySettingsPage'))
const AccountingPage=lazy(()=>import('./pages/AccountingPage'))
const AccountingToolPage=lazy(()=>import('./pages/AccountingToolPage'))
const ReviewQueuePage=lazy(()=>import('./pages/ReviewQueuePage'))
const PositionsPage=lazy(()=>import('./pages/PositionsPage'))
const FocusPage=lazy(()=>import('./pages/FocusPage'))
const RecentActivityPage=lazy(()=>import('./pages/RecentActivityPage'))
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
const AlternativeInvestmentsPage=lazy(()=>import('./pages/InvestmentProductPages').then(module=>({default:module.AlternativeInvestmentsPage})))
const FinancialPlatformsPage=lazy(()=>import('./pages/InvestmentProductPages').then(module=>({default:module.FinancialPlatformsPage})))
const SavingCirclesPage=lazy(()=>import('./pages/InvestmentProductPages').then(module=>({default:module.SavingCirclesPage})))
const PropertyPages=lazy(()=>import('./pages/PropertyPages'))
const InvestmentCashFlowsPage=lazy(()=>import('./pages/InvestmentCashFlowsPage'))
const MonthClosePage=lazy(()=>import('./pages/MonthClosePage'))
const ReconciliationView=lazy(()=>import('./pages/ReconciliationView'))

export default function AppRouter() {
  return (
    <BrowserRouter>
      <SetupGate><BetaProfileInitializer />
      <Suspense fallback={<div className="app-route-loading">Loading WealthOS…</div>}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route
            path="/"
            element={<PortfolioDashboardPage />}
          />

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
          <Route path="/investing/brokers" element={<BrokersPage />} />
          <Route path="/investing/platforms" element={<FinancialPlatformsPage />} />
          <Route path="/investing/alternative-investments" element={<AlternativeInvestmentsPage />} />
          <Route path="/investing/saving-circles" element={<SavingCirclesPage />} />
          <Route path="/focus" element={<FocusPage />} />
          <Route path="/activity" element={<RecentActivityPage />} />
          <Route path="/search" element={<SearchResultsPage />} />
          <Route path="/library" element={<LibraryPage />} />
          <Route path="/index" element={<SystemIndexPage />} />
          <Route path="/bank-accounts" element={<ModulePage module="banking" />} />
          <Route path="/credit-cards" element={<ModulePage module="cards" />} />
          <Route path="/properties" element={<PropertyPages view="summary" />} />
          <Route path="/properties/income" element={<PropertyPages view="income" />} />
          <Route path="/properties/expenses" element={<PropertyPages view="expenses" />} />
          <Route path="/accounting" element={<AccountingPage />} />
          <Route path="/accounting/ledger" element={<AccountingToolPage tool="ledger" />} />
          <Route path="/accounting/journals" element={<AccountingToolPage tool="journals" />} />
          <Route path="/accounting/reconciliation" element={<ReconciliationView standalone />} />
          <Route path="/accounting/review-queue" element={<ReviewQueuePage />} />
          <Route path="/accounting/month-close" element={<MonthClosePage />} />
          <Route path="/reporting" element={<ReportingPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/settings/profile" element={<ProfileSettingsPage />} />
          <Route path="/settings/security" element={<SecuritySettingsPage />} />
          <Route path="/settings/currencies" element={<CurrencySettingsPage />} />
          <Route path="/settings/data-account" element={<DataAccountSettingsPage />} />
        </Route>
      </Routes>
      </Suspense>
      </SetupGate>
    </BrowserRouter>
  )
}
