import { BarChart3, CalendarDays, Check, ChevronDown, Download, FileBarChart, Play, RefreshCw, RotateCcw, Save } from 'lucide-react'
import { useState } from 'react'
import { supportedCurrencies, useCurrency } from '../context/CurrencyContext'
import type { Currency } from '../context/CurrencyContext'
import './ReportingPage.css'
import './ReportingEnhancements.css'
import PageNavigation from '../components/ui/PageNavigation'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useLanguage } from '../context/LanguageContext'
import { displayLocale, formatDisplayInteger, formatDisplayPercent } from '../utils/localeFormat'
import './PageHeaderNavigation.css'
import './ReportingButtonTypography.css'
import './ReportingRefresh.css'

const sources = ['Dividends', 'Deposit interest', 'Fund distributions', 'Private credit', 'Rental income']
const reportTypes = ['Income & reinvestment', 'Cash flow statement', 'Portfolio performance', 'Income by asset', 'Expense analysis', 'Net worth movement', 'Custom report']
const metrics = ['Income received', 'Reinvested amount', 'Cash retained', 'Yield', 'Fees & taxes', 'Net cash flow']
const rows = [
  ['Dividends', 38400, 33600, 4800],
  ['Deposit interest', 18200, 4000, 14200],
  ['Fund distributions', 16800, 15200, 1600],
  ['Private credit', 13000, 10400, 2600],
] as const

export default function ReportingPage() {
  const { currency, enabledCurrencies } = useCurrency()
  const { language, direction, t } = useLanguage()
  const [period, setPeriod] = useState('This month')
  const [reportType, setReportType] = useState(reportTypes[0])
  const [selectedSources, setSelectedSources] = useState(sources.slice(0, 4))
  const [selectedMetrics, setSelectedMetrics] = useState(metrics.slice(0, 3))
  const [generated, setGenerated] = useState(true)
  const [reportCurrency, setReportCurrency] = useState<Currency>(currency)
  const [refreshing, setRefreshing] = useState(false)
  const [updatedAt, setUpdatedAt] = useState(new Date())

  function toggleSource(source: string) {
    setSelectedSources((current) => current.includes(source) ? current.filter((item) => item !== source) : [...current, source])
  }
  function toggleMetric(metric: string) {
    setSelectedMetrics((current) => current.includes(metric) ? current.filter((item) => item !== metric) : [...current, metric])
  }

  const visibleRows = rows.filter(([name]) => selectedSources.includes(name))
  const totals = visibleRows.reduce((sum, row) => [sum[0] + row[1], sum[1] + row[2], sum[2] + row[3]], [0, 0, 0])
  const rate = totals[0] ? (totals[1] / totals[0]) * 100 : 0
  const reportMoney = (value: number) => {
    const targetRate = supportedCurrencies.find((item) => item.code === reportCurrency)?.sarRate ?? 1
    const converted = value / targetRate
    const number = new Intl.NumberFormat(displayLocale(language), { maximumFractionDigits: reportCurrency === 'JPY' ? 0 : 2 }).format(converted)
    const symbol = supportedCurrencies.find((item) => item.code === reportCurrency)?.symbol ?? reportCurrency
    const formattedValue = reportCurrency === 'SAR' ? `\u20C1 ${number}` : `${symbol}${number}`
    return <FormattedMoney value={formattedValue} currency={reportCurrency}/>
  }
  function refreshReport() {
    if (refreshing) return
    setRefreshing(true)
    window.setTimeout(() => { setUpdatedAt(new Date()); setGenerated(true); setRefreshing(false) }, 550)
  }
  function resetReport() {
    setReportType('Custom report')
    setPeriod('This month')
    setSelectedSources([])
    setSelectedMetrics([])
    setReportCurrency(currency)
    setGenerated(false)
  }

  return <section className="reporting-page" dir={direction}>
    <header className="reporting-page__header">
      <div><p>{t('Financial intelligence')}</p><h1>{t('Report Studio')}</h1><span>{t('Build focused reports from your income, cash flows, and investment activity.')}</span></div>
      <div><PageNavigation/><button><Save size={15}/> {t('Save template')}</button><button><Download size={15}/> {t('Export')}</button></div>
    </header>

    <div className="reporting-page__layout">
      <aside className="report-builder">
        <div className="report-builder__title"><span><FileBarChart size={18}/></span><div><h2>{t('Build your report')}</h2><p>{t('Choose what you want to analyze.')}</p></div></div>
        <section><label>{t('Report type')}</label><div className="report-builder__native-select"><select value={reportType} onChange={(event)=>setReportType(event.target.value)}>{reportTypes.map((type)=><option key={type} value={type}>{t(type)}</option>)}</select><ChevronDown size={14}/></div></section>
        <section><label>{t('Period')}</label><div className="report-builder__periods">{['This month','Quarter','YTD','Custom'].map((item)=><button className={period===item?'is-active':''} type="button" onClick={()=>setPeriod(item)} key={item}>{t(item)}</button>)}</div></section>
        <section><label><CalendarDays size={13}/> {t('Date range')}</label><div className="report-builder__dates"><input type="date" defaultValue="2026-08-01"/><span>{t('to')}</span><input type="date" defaultValue="2026-08-31"/></div></section>
        <section><label>{t('Income sources')}</label><div className="report-builder__checks">{sources.map((source)=><button type="button" onClick={()=>toggleSource(source)} className={selectedSources.includes(source)?'is-selected':''} key={source}><i>{selectedSources.includes(source)&&<Check size={11}/>}</i>{t(source)}</button>)}</div></section>
        {(reportType === 'Custom report' || reportType === 'Income & reinvestment') && <section><label>{t('Metrics to include')}</label><div className="report-builder__metric-grid">{metrics.map((metric)=><button type="button" onClick={()=>toggleMetric(metric)} className={selectedMetrics.includes(metric)?'is-selected':''} key={metric}>{selectedMetrics.includes(metric)&&<Check size={10}/>} {t(metric)}</button>)}</div></section>}
        <section><label>{t('Scope')}</label><button className="report-builder__select">{t('All portfolios & assets')} <ChevronDown size={14}/></button></section>
        <section><label>{t('Report currency')}</label><div className="report-builder__native-select"><select value={reportCurrency} onChange={(event)=>setReportCurrency(event.target.value as Currency)}>{enabledCurrencies.map((code)=><option value={code} key={code}>{code} — {t(supportedCurrencies.find((item)=>item.code===code)?.name ?? code)}</option>)}</select><ChevronDown size={14}/></div></section>
        <button className="report-builder__generate" type="button" onClick={()=>{setGenerated(true);setUpdatedAt(new Date())}}><Play size={15}/> {t('Generate report')}</button>
      </aside>

      <main className="report-preview">
        <div className="report-preview__heading"><div><p>{t(period)} • {reportCurrency}</p><h2>{reportType === 'Custom report' ? t('Customized Wealth Report') : t(reportType)}</h2><span>{reportType === 'Custom report' ? `${formatDisplayInteger(selectedMetrics.length,language)} ${t('selected metrics')} • ${formatDisplayInteger(selectedSources.length,language)} ${t('data sources')}` : `${t('Updated')} ${updatedAt.toLocaleTimeString(displayLocale(language), {hour:'2-digit',minute:'2-digit'})}`}</span></div><div className="report-preview__controls"><button type="button" onClick={resetReport}><RotateCcw size={14}/> {t('Reset')}</button><button type="button" disabled={refreshing || !generated} onClick={refreshReport}><RefreshCw className={refreshing?'is-spinning':''} size={14}/> {t(refreshing?'Refreshing…':'Refresh')}</button></div></div>
        {generated && <>
          <div className="report-preview__metrics">
            <article><span>{t('Total income')}</span><strong>{reportMoney(totals[0])}</strong><small>{t('Received during period')}</small></article>
            <article><span>{t('Reinvested')}</span><strong>{reportMoney(totals[1])}</strong><small>{formatDisplayPercent(rate,1,language)} {t('of income')}</small></article>
            <article><span>{t('Retained cash')}</span><strong>{reportMoney(totals[2])}</strong><small>{t('Available liquidity')}</small></article>
          </div>

          <section className="report-preview__chart">
            <div className="report-preview__section-title"><div><h3>{t('Income allocation')}</h3><p>{t('How received income was used')}</p></div><BarChart3 size={17}/></div>
            <div className="report-preview__allocation"><div style={{width:`${rate}%`}}/><span style={{width:`${100-rate}%`}}/></div>
            <div className="report-preview__legend"><span><i/>{t('Reinvested')} <strong>{formatDisplayPercent(rate,1,language)}</strong></span><span><i/>{t('Retained as cash')} <strong>{formatDisplayPercent(100-rate,1,language)}</strong></span></div>
          </section>

          <section className="report-preview__breakdown">
            <div className="report-preview__section-title"><div><h3>{t('Income source breakdown')}</h3><p>{t('Income, reinvestment, and remaining cash by source')}</p></div></div>
            <div className="report-preview__table-head"><span>{t('Source')}</span><span>{t('Income')}</span><span>{t('Reinvested')}</span><span>{t('Retained cash')}</span></div>
            {visibleRows.map(([name,income,reinvested,cash])=><div className="report-preview__row" key={name}><span>{t(name)}</span><strong>{reportMoney(income)}</strong><strong>{reportMoney(reinvested)}</strong><strong>{reportMoney(cash)}</strong></div>)}
            <div className="report-preview__total"><span>{t('Total')}</span><strong>{reportMoney(totals[0])}</strong><strong>{reportMoney(totals[1])}</strong><strong>{reportMoney(totals[2])}</strong></div>
          </section>
        </>}
        {!generated && <div className="report-preview__empty"><span><FileBarChart size={24}/></span><h3>{t('Build a new report')}</h3><p>{t('Select the report type, sources, metrics, period, and currency, then generate a fresh report.')}</p></div>}
      </main>
    </div>
  </section>
}
