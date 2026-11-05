import { ArrowRight, ChartNoAxesCombined, CircleDollarSign, GitBranch, LineChart, PieChart, TrendingUp, WalletCards } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import FormattedMoney from '../components/ui/FormattedMoney'
import PageHeader from '../components/ui/PageHeader'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { usePortfolio } from '../hooks/usePortfolio'
import { getConsolidatedPerformanceHistory, type PortfolioPerformanceHistory } from '../services/portfolioService'
import { getWealthAnalytics, type WealthAnalytics } from '../services/accountingService'
import { formatDisplayPercent } from '../utils/localeFormat'
import './AnalyticsPage.css'

type Period = PortfolioPerformanceHistory['period']
type RankedItem = { label: string; value: number; kind: string }

const linePath = (values: number[]) => {
  if (values.length < 2) return 'M0 78 L600 78'
  const min = Math.min(...values)
  const max = Math.max(...values)
  const range = max - min
  return values.map((value, index) => {
    const x = index / (values.length - 1) * 600
    const y = range === 0 ? 78 : 130 - ((value - min) / range) * 104
    return `${index ? 'L' : 'M'}${x.toFixed(1)} ${y.toFixed(1)}`
  }).join(' ')
}

export default function AnalyticsPage(){
  const { t, language } = useLanguage()
  const { formatMoney } = useCurrency()
  const financial = useFinancialSummary()
  const portfolio = usePortfolio('consolidated')
  const [period,setPeriod] = useState<Period>('YTD')
  const [history,setHistory] = useState<PortfolioPerformanceHistory|null>(null)
  const [analytics,setAnalytics] = useState<WealthAnalytics|null>(null)

  useEffect(()=>{let active=true;Promise.all([getConsolidatedPerformanceHistory(period),getWealthAnalytics(period)]).then(([nextHistory,nextAnalytics])=>{if(active){setHistory(nextHistory);setAnalytics(nextAnalytics)}}).catch(()=>{if(active){setHistory(null);setAnalytics(null)}});return()=>{active=false}},[period])

  const incomeLeaders = useMemo<RankedItem[]>(()=>{
    if(!financial.data)return[]
    const items:RankedItem[] = []
    Object.entries(financial.data.investment_distributions_by_symbol).forEach(([label,value])=>{if(Number(value)>0)items.push({label,value:Number(value),kind:'Distribution'})})
    Object.entries(financial.data.realized_price_return_by_portfolio).forEach(([label,value])=>{if(Number(value)>0)items.push({label,value:Number(value),kind:'Realized gain'})})
    if(financial.data.rental_income_ttm>0)items.push({label:t('Investment Properties'),value:financial.data.rental_income_ttm,kind:'Rental income'})
    return items.sort((a,b)=>b.value-a.value).slice(0,6)
  },[financial.data,t])

  if(financial.loading||portfolio.loading)return <main className="analytics-page__state">{t('Loading WealthOS...')}</main>
  if(financial.error||portfolio.error)return <main className="analytics-page__state is-error">{t('Failed to load financial data')}</main>
  if(!financial.data||!portfolio.data)return <main className="analytics-page__state">{t('Data Unavailable')}</main>

  const summary=financial.data
  const portfolioSummary=portfolio.data.summary
  const assetRows=summary.asset_breakdown.filter(item=>Number(item.balance)>0).sort((a,b)=>Number(b.balance)-Number(a.balance)).slice(0,8)
  const largestAsset=Math.max(...assetRows.map(item=>Number(item.balance)),1)
  const largestIncome=Math.max(...incomeLeaders.map(item=>item.value),1)
  const historyValues=history?.points.map(point=>Number(point.market_value))??[]
  const path=linePath(historyValues)
  const area=`${path} L600 148 L0 148 Z`
  const periodReturn=Number(history?.percentage??0)
  const positive=periodReturn>=0

  return <section className="analytics-page">
    <PageHeader title={t('Wealth Analytics')} subtitle={t('Understand what produced your wealth growth, where returns went, and how every asset contributed.')} icon={ChartNoAxesCombined} actions={<nav className="analytics-page__periods" aria-label={t('Analysis period')}>{(['1W','1M','YTD','1Y'] as Period[]).map(value=><button type="button" className={period===value?'is-active':''} aria-pressed={period===value} onClick={()=>setPeriod(value)} key={value}>{value}</button>)}</nav>}/>

    <div className="analytics-page__primary-grid">
      <section className="analytics-panel analytics-panel--trend">
        <header><div><span><LineChart size={17}/></span><div><h2>{t('Growth Over Time')}</h2><p>{t('Market portfolios for the selected period')}</p></div></div><strong>{history?.has_sufficient_history?<FormattedMoney value={formatMoney(Number(history.change))} sign={Number(history.change)>=0?'+':''}/>:t('Building history')}</strong></header>
        <div className={`analytics-trend ${positive?'is-positive':'is-negative'}`}>
          <svg viewBox="0 0 600 150" role="img" aria-label={t('Market portfolio value trend')} preserveAspectRatio="none"><line x1="0" y1="78" x2="600" y2="78"/><path className="analytics-trend__area" d={area}/><path className="analytics-trend__line" d={path}/></svg>
          {!history?.has_sufficient_history?<div className="analytics-trend__empty">{t('Historical comparisons will become more accurate as monthly snapshots accumulate.')}</div>:null}
        </div>
      </section>

      <section className="analytics-panel analytics-panel--source">
        <header><div><span><GitBranch size={17}/></span><div><h2>{t('Source of Wealth Growth')}</h2><p>{t('Separate your funding from investment-created growth')}</p></div></div></header>
        <div className="analytics-source">
          <div><span>{t('Owner funding')}</span><strong><FormattedMoney value={formatMoney(Number(analytics?.growth_sources.owner_funding??0))}/></strong></div>
          <div><span>{t('Unrealized market growth')}</span><strong><FormattedMoney value={formatMoney(portfolioSummary.unrealized_pl)}/></strong></div>
          <div><span>{t('Realized price gains')}</span><strong><FormattedMoney value={formatMoney(summary.realized_price_return_total)}/></strong></div>
          <div><span>{t('Recorded investment income')}</span><strong><FormattedMoney value={formatMoney(Number(analytics?.growth_sources.investment_income??0))}/></strong></div>
        </div>
        <p className="analytics-panel__note">{t('Internal transfers are excluded from income and wealth growth.')} <FormattedMoney value={formatMoney(Number(analytics?.transfer_excluded_total??0))}/> {t('excluded in this period.')}</p>
      </section>
    </div>

    <div className="analytics-page__secondary-grid">
      <section className="analytics-panel">
        <header><div><span><TrendingUp size={17}/></span><div><h2>{t('Top Income Producers')}</h2><p>{t('Ranked by recorded realized cash income')}</p></div></div><Link to="/investing/cash-flows">{t('Cash flows')} <ArrowRight size={14}/></Link></header>
        <div className="analytics-ranking">{incomeLeaders.length?incomeLeaders.map(item=><div key={`${item.kind}-${item.label}`}><div><span><strong>{item.label}</strong><small>{t(item.kind)}</small></span><strong><FormattedMoney value={formatMoney(item.value)}/></strong></div><i><b style={{width:`${Math.max(item.value/largestIncome*100,3)}%`}}/></i></div>):<p className="analytics-panel__empty">{t('Recorded investment income will appear here.')}</p>}</div>
      </section>

      <section className="analytics-panel">
        <header><div><span><PieChart size={17}/></span><div><h2>{t('Asset Growth Base')}</h2><p>{t('Where current asset value is concentrated')}</p></div></div></header>
        <div className="analytics-ranking analytics-ranking--assets">{assetRows.map(item=><div key={item.code}><div><span><strong>{t(item.name)}</strong><small>{summary.total_assets>0?formatDisplayPercent(Number(item.balance)/summary.total_assets*100,1,language):'—'}</small></span><strong><FormattedMoney value={formatMoney(Number(item.balance))}/></strong></div><i><b style={{width:`${Math.max(Number(item.balance)/largestAsset*100,2)}%`}}/></i></div>)}</div>
      </section>
    </div>

    <section className="analytics-panel analytics-panel--flow">
      <header><div><span><CircleDollarSign size={17}/></span><div><h2>{t('Where the Money Went')}</h2><p>{t('Follow returns from receipt to their final destination')}</p></div></div><Link to="/investing/cash-flows">{t('Investment Cash Flows')} <ArrowRight size={14}/></Link></header>
      <div className="analytics-flow">
        <div><span><WalletCards size={16}/></span><small>{t('Cash retained')}</small><strong><FormattedMoney value={formatMoney(Number(analytics?.destinations.cash_retained??0))}/></strong></div><ArrowRight aria-hidden="true"/><div><span><TrendingUp size={16}/></span><small>{t('Reinvested')}</small><strong><FormattedMoney value={formatMoney(Number(analytics?.destinations.reinvested??0))}/></strong></div><ArrowRight aria-hidden="true"/><div><span><GitBranch size={16}/></span><small>{t('Spent')}</small><strong><FormattedMoney value={formatMoney(Number(analytics?.destinations.spent??0))}/></strong></div>
      </div>
      <p className="analytics-panel__note">{t('Classification coverage')}: {formatDisplayPercent(Number(analytics?.classification_coverage??0),1,language)}. {t('Unknown movements remain visible instead of being guessed.')}</p>
    </section>
  </section>
}
