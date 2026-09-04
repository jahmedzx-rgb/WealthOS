import { ChartNoAxesCombined, LayoutDashboard, ShieldCheck } from 'lucide-react'
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'

import './PortfolioDashboardPage.css'

import FinancialSnapshot from '../components/dashboard/FinancialSnapshot'
import FinancialHealthCard from '../components/dashboard/FinancialHealthCard'
import FocusToday from '../components/dashboard/FocusToday'
import Operations from '../components/dashboard/Operations'
import RecentActivity from '../components/dashboard/RecentActivity'
import WealthAllocationOverview from '../components/dashboard/WealthAllocationOverview'
import { usePortfolio } from '../hooks/usePortfolio'
import { useCurrency } from '../context/CurrencyContext'
import FormattedMoney from '../components/ui/FormattedMoney'
import { formatDateTime } from '../utils/dateFormat'
import PageHeader from '../components/ui/PageHeader'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { getConsolidatedPerformanceHistory, updateMarketPrices, type PortfolioPerformanceHistory } from '../services/portfolioService'
import { useLanguage } from '../context/LanguageContext'

export default function PortfolioDashboardPage() {
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const [selectedPeriod, setSelectedPeriod] = useState<'1W' | '1M' | '1Y' | 'YTD'>('YTD')
  const [performanceHistory, setPerformanceHistory] = useState<PortfolioPerformanceHistory | null>(null)
  const [lastUpdatedAt, setLastUpdatedAt] = useState(() => {
    const saved = localStorage.getItem('wealthos-dashboard-last-updated')
    const parsed = saved ? new Date(saved) : new Date()
    return Number.isNaN(parsed.getTime()) ? new Date() : parsed
  })

  const {
    data,
    loading,
    error,
    refresh,
  } = usePortfolio('consolidated')
  const financial = useFinancialSummary()

  useEffect(()=>{let active=true;updateMarketPrices().then(()=>{if(active)return refresh()}).catch(()=>undefined);return()=>{active=false}},[refresh])

  useEffect(() => {
    let active = true
    getConsolidatedPerformanceHistory(selectedPeriod)
      .then((result) => { if (active) setPerformanceHistory(result) })
      .catch(() => { if (active) setPerformanceHistory(null) })
    return () => { active = false }
  }, [selectedPeriod, data])

  useEffect(() => {
    if (!data || !financial.data) return
    const signature = JSON.stringify({
      portfolio: data.summary,
      positions: data.positions,
      allocation: data.allocation_summary,
      financial: {
        total_assets: financial.data.total_assets,
        total_liabilities: financial.data.total_liabilities,
        net_worth: financial.data.net_worth,
        available_cash: financial.data.available_cash,
        cash_inflow: financial.data.cash_inflow,
        cash_outflow: financial.data.cash_outflow,
        net_cash_flow: financial.data.net_cash_flow,
        monthly_income: financial.data.monthly_income,
        monthly_expenses: financial.data.monthly_expenses,
        asset_breakdown: financial.data.asset_breakdown,
        liability_breakdown: financial.data.liability_breakdown,
        cash_accounts: financial.data.cash_accounts,
        recent_activity: financial.data.recent_activity,
      },
    })
    const previousSignature = localStorage.getItem('wealthos-dashboard-data-signature')
    const previousTimestamp = localStorage.getItem('wealthos-dashboard-last-updated')
    if (previousSignature === signature && previousTimestamp) {
      const saved = new Date(previousTimestamp)
      if (!Number.isNaN(saved.getTime())) queueMicrotask(() => setLastUpdatedAt(saved))
      return
    }
    const changedAt = new Date()
    localStorage.setItem('wealthos-dashboard-data-signature', signature)
    localStorage.setItem('wealthos-dashboard-last-updated', changedAt.toISOString())
    queueMicrotask(() => setLastUpdatedAt(changedAt))
  }, [data, financial.data])

  if (loading || financial.loading) {
    return <main>{t('Loading WealthOS...')}</main>
  }

  if (error || financial.error) {
    return (
      <main>
        {t('Failed to load financial data')}: {error || financial.error}
      </main>
    )
  }

  if (!data || !financial.data) {
    return <main>{t('No portfolio data.')}</main>
  }

  const portfolioCurrency = data.portfolio.base_currency_code as Parameters<typeof formatMoney>[1]
  const formatCurrency = (value: number) => formatMoney(value, portfolioCurrency)

  const formatCompactCurrency = (value: number) => formatMoney(value, portfolioCurrency, true)

  // Accounting assets are recorded at cost; live unrealized P/L marks investments to market.
  const consolidatedNetWorth = financial.data.net_worth + data.summary.unrealized_pl
  const availableCash = financial.data.available_cash

  const hasPerformanceHistory = performanceHistory?.has_sufficient_history === true
  const periodPerformance = { percentage: Number(performanceHistory?.percentage ?? 0), value: Number(performanceHistory?.change ?? 0) }
  const positivePerformance = periodPerformance.percentage >= 0
  const performanceClass = positivePerformance ? 'is-positive' : 'is-negative'
  const performanceSign = positivePerformance ? '+' : ''
  const historyValues = performanceHistory?.points.map((point) => Number(point.market_value)) ?? []
  const historyMin = historyValues.length ? Math.min(...historyValues) : 0
  const historyMax = historyValues.length ? Math.max(...historyValues) : 0
  const historyRange = historyMax - historyMin
  const trendLinePath = historyValues.length >= 2
    ? historyValues.map((value, index) => {
      const x = (index / (historyValues.length - 1)) * 520
      const y = historyRange === 0 ? 36 : 59 - ((value - historyMin) / historyRange) * 46
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(1)} ${y.toFixed(1)}`
    }).join(' ')
    : 'M0 36 L520 36'
  const trendAreaPath = `${trendLinePath} L520 72 L0 72 Z`
  const trendEndY = historyValues.length >= 2 && historyRange !== 0 ? 59 - ((historyValues.at(-1)! - historyMin) / historyRange) * 46 : 36

  return (
    <section className="portfolio-dashboard">
      <PageHeader hideNavigation title={t('PRIVATE WEALTH DASHBOARD')} subtitle={t('Consolidated assets, liquidity, obligations, and performance.')} icon={LayoutDashboard} actions={<div className="portfolio-dashboard__overview-controls">
          <div className="portfolio-dashboard__periods" aria-label={t('Performance period')}>
            {(['1W', '1M', '1Y', 'YTD'] as const).map((period) => (
              <button
                className={selectedPeriod === period ? 'is-active' : undefined}
                type="button"
                aria-pressed={selectedPeriod === period}
                onClick={() => setSelectedPeriod(period)}
                key={period}
              >
                {period}
              </button>
            ))}
          </div>
          <p className="portfolio-dashboard__updated">
            {t('Last updated')} · {formatDateTime(lastUpdatedAt)}
          </p>
          <Link className={`portfolio-dashboard__books is-${financial.data.accounting_period.current_status.toLowerCase()}`} to="/accounting/month-close">{t('Monthly Snapshot')} · {t(financial.data.accounting_period.current_status==='SAVED'?'Saved':'Current')} →</Link>
        </div>}/>

      <main className="portfolio-dashboard__main">
        <section className="portfolio-dashboard__insights">
          <div className="portfolio-dashboard__insight-group">
            <header className="portfolio-dashboard__insight-title"><span><ChartNoAxesCombined size={18}/></span><div><h2>{t('Wealth Trend')}</h2><small>{t('Performance')}</small></div></header>
            <section className={`portfolio-dashboard__trend ${performanceClass}`} aria-label={t('Wealth and investment trend')}>
              <svg viewBox="0 0 520 72" role="img" aria-label={`${selectedPeriod} portfolio ${positivePerformance ? 'growth' : 'loss'} trend`}>
              <line className="portfolio-dashboard__trend-baseline" x1="0" y1="36" x2="520" y2="36" />
              <path className="portfolio-dashboard__trend-area" d={trendAreaPath} />
              <path className="portfolio-dashboard__trend-line" d={trendLinePath} />
              <circle className="portfolio-dashboard__trend-point" cx="520" cy={trendEndY} r="5" />
              </svg>
              <div className="portfolio-dashboard__trend-metrics">
              <div className="portfolio-dashboard__trend-current">
                <span>{t('Net Worth')}</span>
                <strong><FormattedMoney value={formatMoney(consolidatedNetWorth, 'SAR')}/></strong>
              </div>
              <div className="portfolio-dashboard__growth-metric">
                <span>{t('Return')}</span>
                <strong>{hasPerformanceHistory?<FormattedMoney value={formatCompactCurrency(periodPerformance.value)} sign={positivePerformance?'+':''}/>:<span>—</span>}</strong>
                <small className={hasPerformanceHistory ? undefined : 'is-building'}>{hasPerformanceHistory?`${performanceSign}${periodPerformance.percentage.toFixed(1)}%`:t('Building history')}</small>
              </div>
              </div>
            </section>
          </div>
          <div className="portfolio-dashboard__insight-group">
            <header className="portfolio-dashboard__insight-title"><span><ShieldCheck size={18}/></span><div><h2>{t('Financial Health')}</h2><small>{t('Assets, liquidity, obligations, and risk')}</small></div></header>
            <FinancialHealthCard cash={formatMoney(availableCash, 'SAR')} investments={formatCurrency(data.summary.market_value)} dbr={financial.data.dbr} score={financial.data.health_score} riskLevel={financial.data.risk_level}/>
          </div>
        </section>

        <section className="portfolio-dashboard__workspace">
          <div className="portfolio-dashboard__focus">
            <FocusToday />
          </div>

          <div className="portfolio-dashboard__operations">
            <Operations />
          </div>

          <div className="portfolio-dashboard__activity">
            <RecentActivity activities={financial.data.recent_activity}/>
          </div>
        </section>

        <FinancialSnapshot summary={financial.data}/>

        <WealthAllocationOverview allocation={data.allocation_summary} positions={data.positions} totalValue={data.summary.market_value} portfolioCurrency={portfolioCurrency} assetBreakdown={financial.data.asset_breakdown} deposits={financial.data.deposits} realEstateReturn={financial.data.real_estate_return} />

      </main>
    </section>
  )
}
