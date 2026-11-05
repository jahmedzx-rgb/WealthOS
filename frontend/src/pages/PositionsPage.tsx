import { CalendarRange, ChartCandlestick, ChartNoAxesCombined, ChartSpline, ChevronLeft, ChevronRight, Clock3, HandCoins, Layers3, Pencil, Radio, Wallet } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import PositionsTable from '../components/portfolio/PositionsTable'
import { usePortfolio } from '../hooks/usePortfolio'
import { usePortfolioPriceSync } from '../hooks/usePortfolioPriceSync'
import { supportedCurrencies, useCurrency } from '../context/CurrencyContext'
import './PositionsPage.css'
import { displayLocale, formatDisplayPercent } from '../utils/localeFormat'
import './InvestingSubpages.css'
import { marketPriceCoverageLabels } from '../utils/marketPriceFreshness'
import { useLanguage } from '../context/LanguageContext'
import { getMonthlyActivity, type FinancialActivity } from '../services/accountingService'
import { getConsolidatedMonthEnd, getPortfolioMonthEnd, getPortfolios, type PortfolioLookup, type PortfolioMonthEnd } from '../services/portfolioService'
import { formatDateTime } from '../utils/dateFormat'
import { activityDetail, activityTitle } from '../utils/activityLabels'
import { useFinancialSummary } from '../hooks/useFinancialSummary'

export default function PositionsPage() {
  const [searchParams]=useSearchParams()
  const requestedType=searchParams.get('type')?.toUpperCase()??''
  const portfolioId = 'consolidated' as const
  const { data, loading, error, refresh } = usePortfolio(portfolioId)
  const financial = useFinancialSummary(true)
  const { formatMoney } = useCurrency()
  const { t,language } = useLanguage()
  const [portfolioList,setPortfolioList]=useState<PortfolioLookup[]>([])
  const [selectedPortfolio,setSelectedPortfolio]=useState<'all'|number>('all')
  const [history,setHistory]=useState<FinancialActivity[]>([])
  const [editMenuOpen,setEditMenuOpen]=useState(false)
  const now=new Date()
  const [period,setPeriod]=useState(()=>({year:now.getFullYear(),month:now.getMonth()+1}))
  const [monthEnd,setMonthEnd]=useState<PortfolioMonthEnd|null>(null)
  const currentPeriod=period.year===now.getFullYear()&&period.month===now.getMonth()+1
  const [failedPriceIds,setFailedPriceIds]=useState<number[]>([])
  usePortfolioPriceSync(data?.positions, refresh, currentPeriod, result=>setFailedPriceIds(result.failed_security_ids??[]))
  const monthLabel=new Intl.DateTimeFormat(displayLocale(language),{month:'long',year:'numeric'}).format(new Date(period.year,period.month-1,1))
  useEffect(()=>{getPortfolios().then(setPortfolioList).catch(()=>setPortfolioList([]))},[])
  useEffect(()=>{let live=true;getMonthlyActivity(period.year,period.month).then(activity=>{if(live)setHistory(activity)}).catch(()=>{if(live)setHistory([])});return()=>{live=false}},[period])
  useEffect(()=>{if(currentPeriod){setMonthEnd(null);return}let live=true;setMonthEnd(null);const request=selectedPortfolio==='all'?getConsolidatedMonthEnd(period.year,period.month):getPortfolioMonthEnd(selectedPortfolio,period.year,period.month);request.then(value=>{if(live)setMonthEnd(value)}).catch(()=>{if(live)setMonthEnd({available:false,year:period.year,month:period.month})});return()=>{live=false}},[currentPeriod,period,selectedPortfolio])
  function moveMonth(change:number){setPeriod(current=>{const date=new Date(current.year,current.month-1+change,1);return{year:date.getFullYear(),month:date.getMonth()+1}})}
  const activePortfolio=selectedPortfolio==='all'?null:portfolioList.find(item=>item.id===selectedPortfolio)??null
  const visiblePositions=data?.positions.filter(position=>(!requestedType||(position.allocation_type??position.security_type)===requestedType)&&(selectedPortfolio==='all'||position.portfolio_id===selectedPortfolio))??[]
  const historicalPositions=(monthEnd?.positions??[]).filter(position=>(!requestedType||position.security_type===requestedType)&&(selectedPortfolio==='all'||position.portfolio_id===selectedPortfolio))
  const historicalGroups=portfolioList.filter(portfolio=>(monthEnd?.historical_portfolio_ids??[]).includes(portfolio.id)&&(selectedPortfolio==='all'||portfolio.id===selectedPortfolio)).map(portfolio=>{
    const sourcePositions=historicalPositions.filter(position=>position.portfolio_id===portfolio.id)
     const allHistoricalPositions=(monthEnd?.positions??[]).filter(position=>position.portfolio_id===portfolio.id)
     const portfolioSarRate=supportedCurrencies.find(currency=>currency.code===portfolio.base_currency_code)?.sarRate??1
     const originalInvestment=allHistoricalPositions.reduce((sum,position)=>sum+(position.total_cost_base??position.total_cost),0)/portfolioSarRate
    const marketValue=sourcePositions.reduce((sum,position)=>sum+(position.market_value_base??0),0)
    const comparableMarketValue=sourcePositions.reduce((sum,position)=>sum+(position.market_value_base??position.market_value??0),0)
    const positions=sourcePositions.map(position=>{
      const livePosition=data?.positions.find(item=>item.security_id===position.security_id)
      return{...position,exchange:livePosition?.exchange??'',next_distribution_date:null,expected_distribution_amount:null,distribution_frequency:null,fair_value:null,weight:marketValue?(position.market_value_base??0)/marketValue:0,trade_history:[]}
    })
     return{portfolio,positions,marketValue,comparableMarketValue,originalInvestment}
  }).filter(group=>group.positions.length>0).sort((left,right)=>right.comparableMarketValue-left.comparableMarketValue)
  const fullPortfolioView=selectedPortfolio==='all'&&!requestedType
  const totalCost=fullPortfolioView?(data?.summary.total_cost??0):visiblePositions.reduce((sum,item)=>sum+item.total_cost,0)
  const marketValue=fullPortfolioView?(data?.summary.market_value??0):visiblePositions.reduce((sum,item)=>sum+item.market_value,0)
  const cashValue=selectedPortfolio==='all'?portfolioList.reduce((sum,item)=>sum+item.cash_balance*(supportedCurrencies.find(currency=>currency.code===item.base_currency_code)?.sarRate??1),0):(activePortfolio?.cash_balance??0)
  const portfolioValue=marketValue+cashValue
  const unrealized=fullPortfolioView?(data?.summary.unrealized_pl??0):visiblePositions.reduce((sum,item)=>sum+item.unrealized_pl,0)
  const displayCurrency=(activePortfolio?.base_currency_code??data?.portfolio.base_currency_code) as Parameters<typeof formatMoney>[1]
  const convertReturn=(amount:number,sourceCurrency:string)=>amount*(supportedCurrencies.find(item=>item.code===sourceCurrency)?.sarRate??1)/(supportedCurrencies.find(item=>item.code===displayCurrency)?.sarRate??1)
  const distributionByPortfolio=financial.data?.investment_distributions_by_portfolio_currency
  const distributionRows=selectedPortfolio==='all'?Object.entries(distributionByPortfolio??{}).flatMap(([portfolioId,currencies])=>Object.entries(currencies).map(([currency,amount])=>({portfolioId,currency,amount}))):(Object.entries(distributionByPortfolio?.[String(selectedPortfolio)]??{}).map(([currency,amount])=>({portfolioId:String(selectedPortfolio),currency,amount})))
  const recordedDistributions=selectedPortfolio==='all'
    ? Object.entries(financial.data?.investment_distributions_by_currency??{}).reduce((sum,[currency,amount])=>sum+convertReturn(amount,currency),0)
    : distributionRows.length
      ? distributionRows.reduce((sum,row)=>sum+convertReturn(row.amount,row.currency),0)
      : visiblePositions.reduce((sum,item)=>Object.entries(financial.data?.investment_distributions_by_symbol_currency?.[item.symbol.toUpperCase()]??{}).reduce((symbolTotal,[currency,amount])=>symbolTotal+convertReturn(amount,currency),sum),0)
  const realizedRows=Object.entries(financial.data?.realized_price_return_by_portfolio??{}).filter(([portfolioId])=>selectedPortfolio==='all'||portfolioId===String(selectedPortfolio))
  const realizedPriceReturn=realizedRows.reduce((sum,[portfolioId,amount])=>{const sourceCurrency=portfolioList.find(item=>String(item.id)===portfolioId)?.base_currency_code??displayCurrency??'SAR';return sum+convertReturn(amount,sourceCurrency)},0)
  const totalReturns=realizedPriceReturn+recordedDistributions
  const totalReturnsPercentage=totalCost?totalReturns/totalCost*100:0
  const displayedMarketValue=!currentPeriod&&monthEnd?.available?Number(monthEnd.market_value??0):marketValue
  const displayedUnrealized=!currentPeriod&&monthEnd?.available?Number(monthEnd.unrealized_pl??0):unrealized
  const displayedCost=!currentPeriod&&monthEnd?.available?Number(monthEnd.total_cost??0):totalCost
  const historicalComplete=Boolean(monthEnd?.positions_complete)
  const displayedReturnPercentage=displayedCost?displayedUnrealized/displayedCost*100:0
  const priceCoverage=marketPriceCoverageLabels(visiblePositions)
  const localizedCoverage=priceCoverage.map(line=>line.replace('No Market Prices Yet',t('No Market Prices Yet')).replace('Previous Close',t('Previous Close')).replace('Market Closed',t('Market Closed')).replace('Live',t('Live')).replace('Delayed',t('Delayed')).replace('As Of',t('As Of')))
  const failedPriceSymbols=[...new Set((data?.positions??[]).filter(position=>failedPriceIds.includes(position.security_id)).map(position=>position.symbol))]
  const tickerLines=[...(currentPeriod?localizedCoverage:[monthEnd?.available?`${t('Month-end market snapshot')} · ${monthEnd.as_of_date}`:t('No portfolio valuation was recorded for this month.')]),...(currentPeriod&&failedPriceSymbols.length?[`${t('Price update unavailable')} · ${failedPriceSymbols.join(', ')}`]:[])]
   const groups=portfolioList.map(portfolio=>{const raw=visiblePositions.filter(position=>position.portfolio_id===portfolio.id);const allPositions=(data?.positions??[]).filter(position=>position.portfolio_id===portfolio.id);const portfolioSarRate=supportedCurrencies.find(currency=>currency.code===portfolio.base_currency_code)?.sarRate??1;const originalInvestment=allPositions.reduce((sum,item)=>sum+(item.total_cost_base??item.total_cost),0)/portfolioSarRate;const groupMarket=raw.reduce((sum,item)=>sum+item.market_value,0);const comparableMarketValue=raw.reduce((sum,item)=>sum+(item.market_value_base??item.market_value),0);return{portfolio,positions:raw.map(item=>({...item,weight:groupMarket?item.market_value/groupMarket:0})),marketValue:groupMarket,comparableMarketValue,originalInvestment,portfolioValue:groupMarket+portfolio.cash_balance}}).filter(group=>group.positions.length).sort((left,right)=>right.comparableMarketValue-left.comparableMarketValue)
  const portfolioIds=useMemo(()=>new Set(portfolioList.map(item=>item.id)),[portfolioList])
  const displayedHistory=history.filter(item=>{const reference=item.related_reference??'';const match=reference.match(/(?:portfolio-created|opening-portfolio(?:-adjustment)?|portfolio):(\d+)/);return Boolean(match&&portfolioIds.has(Number(match[1]))&&(selectedPortfolio==='all'||Number(match[1])===selectedPortfolio))}).slice(0,8)
  const activityPortfolio=(item:FinancialActivity)=>{const match=(item.related_reference??'').match(/(?:portfolio-created|opening-portfolio(?:-adjustment)?|portfolio):(\d+)/);return match?portfolioList.find(portfolio=>portfolio.id===Number(match[1]))??null:null}

  if (loading) return <main className="positions-page__state">{t('Loading positions…')}</main>
  if (error) return <main className="positions-page__state">{t('Unable to load positions:')} {t(error)}</main>
  if (!data) return <main className="positions-page__state">{t('No portfolio positions found.')}</main>

  return <section className="positions-page">
    <PageHeader className="positions-page__header" eyebrow={t('Portfolio Management')} title={t('Investment Positions')} subtitle={t('Review listed holdings, market values, allocation, and unrealized performance.')} icon={ChartCandlestick} actions={<label className="positions-page__portfolio-filter"><span>{t('Portfolio View')}</span><select value={selectedPortfolio} onChange={event=>setSelectedPortfolio(event.target.value==='all'?'all':Number(event.target.value))}><option value="all">{t('All Portfolios')}</option>{portfolioList.map(portfolio=><option value={portfolio.id} key={portfolio.id}>{portfolio.broker_name?`${portfolio.broker_name} · `:''}{portfolio.name}</option>)}</select></label>}/>

    <div className="positions-page__metrics">
      <article><span><Layers3 size={15}/>{t('Positions')}</span><strong>{currentPeriod?visiblePositions.length:monthEnd?.available?historicalPositions.length:'—'}</strong><small>{activePortfolio?.name??t('All Portfolios')}</small></article>
      <article><span><ChartSpline size={15}/>{t('Market value')}</span><strong>{!currentPeriod&&(!monthEnd?.available||!historicalComplete)?'—':<FormattedMoney value={formatMoney(displayedMarketValue,displayCurrency)}/>}</strong></article>
      <article><span><Wallet size={15}/>{t('Total portfolio value')}</span><strong>{!currentPeriod&&(!monthEnd?.available||!historicalComplete)?'—':<FormattedMoney value={formatMoney(currentPeriod?portfolioValue:displayedMarketValue,displayCurrency)}/>}</strong><small>{currentPeriod?`${t('Market value')} + ${t('Cash')}`:t('Month-end market snapshot')}</small></article>
      <article className="positions-page__unrealized"><span><ChartNoAxesCombined size={15}/>{t('Unrealized return')}</span><div className="positions-page__unrealized-value"><strong className={displayedUnrealized >= 0 ? 'is-positive' : 'is-negative'}>{!currentPeriod&&(!monthEnd?.available||!historicalComplete)?'—':<FormattedMoney value={formatMoney(displayedUnrealized,displayCurrency)}/>}</strong><small className={displayedUnrealized >= 0 ? 'is-positive' : 'is-negative'}>{!currentPeriod&&(!monthEnd?.available||!historicalComplete)?'—':formatDisplayPercent(displayedReturnPercentage,2)}</small></div></article>
      <article className="positions-page__total-returns"><span><HandCoins size={15}/>{t('Total Returns')}</span>{currentPeriod?<><div className={`positions-page__total-return-value ${totalReturns>=0?'is-positive':'is-negative'}`}><strong><FormattedMoney value={formatMoney(totalReturns,displayCurrency)}/></strong><b>{formatDisplayPercent(totalReturnsPercentage,2)}</b></div><small><span>{t('Realized price return')} <b><FormattedMoney value={formatMoney(realizedPriceReturn,displayCurrency)}/></b></span><span>{t('Recorded distributions')} <b><FormattedMoney value={formatMoney(recordedDistributions,displayCurrency)}/></b></span></small></>:<div className="positions-page__total-return-value"><strong>—</strong></div>}</article>
      {tickerLines.length?<div className="positions-page__market-ticker" role="status" aria-label={t('Market updates')}>
      <strong><Radio size={14}/>{t('Market updates')}</strong>
      <div><div className="positions-page__ticker-track">
        {[false,true].map(copy=><span className="positions-page__ticker-group" aria-hidden={copy||undefined} key={String(copy)}>{tickerLines.map((line,index)=><span key={`${copy}-${line}`}><i/>{line}{index<tickerLines.length-1?<b>•</b>:null}</span>)}</span>)}
      </div></div>
      </div>:null}
      <nav className="positions-page__month-browser" aria-label={t('Displayed period')}><CalendarRange size={15}/><button type="button" onClick={()=>moveMonth(-1)} aria-label={t('Previous month')}><ChevronLeft size={15}/></button><div><small>{t(currentPeriod?'Current live period':'Historical period')}</small><strong>{monthLabel}</strong></div><button type="button" disabled={currentPeriod} onClick={()=>moveMonth(1)} aria-label={t('Next month')}><ChevronRight size={15}/></button></nav>
    </div>

    {currentPeriod?<div className="positions-page__portfolio-groups">{groups.map(group=><PositionsTable key={group.portfolio.id} portfolioId={group.portfolio.id} positions={group.positions} brokerName={group.portfolio.broker_name} title={`${group.portfolio.broker_name??t('Broker')} · ${group.portfolio.name}`} subtitle={`${t('Initial investment')} · ${formatMoney(group.originalInvestment,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])} · ${t('Market value')} · ${formatMoney(group.marketValue,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])} · ${t('Total portfolio value')} · ${formatMoney(group.portfolioValue,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])}`}/>)}</div>:monthEnd?.available?<div className="positions-page__historical-groups"><div className="positions-page__historical-note"><CalendarRange size={17}/><div><strong>{monthLabel}</strong><small>{t('Month-end market snapshot')} · {monthEnd.as_of_date} · {t('Includes historical position details')}{monthEnd.valuation_snapshot_date&&monthEnd.valuation_snapshot_date!==monthEnd.as_of_date?` · ${t('Original valuation recorded')} ${monthEnd.valuation_snapshot_date}`:''}{!historicalComplete?` · ${t('Historical closing prices unavailable for')} ${monthEnd.missing_symbols?.join(', ')??''}`:''}</small></div></div><div className="positions-page__portfolio-groups">{historicalGroups.map(group=><PositionsTable key={group.portfolio.id} portfolioId={group.portfolio.id} positions={group.positions} historical emptyMessage={t('No open positions for this portfolio on this date.')} brokerName={group.portfolio.broker_name} title={`${group.portfolio.broker_name??t('Broker')} · ${group.portfolio.name}`} subtitle={`${t('Initial investment')} · ${formatMoney(group.originalInvestment,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])} · ${t('Market value')} · ${formatMoney(group.marketValue,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])} · ${t('Total portfolio value')} · ${formatMoney(group.marketValue,group.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])}`}/>)}</div>{!historicalGroups.length?<div className="positions-page__historical-note"><CalendarRange size={17}/><div><strong>{t('No historical positions available')}</strong><small>{t('A valuation total exists, but position-level data could not be reconstructed for this period.')}</small></div></div>:null}</div>:<div className="positions-page__historical-note"><CalendarRange size={17}/><div><strong>{monthLabel}</strong><small>{t('No portfolio valuation was recorded for this month.')}</small></div></div>}
    <section className="positions-page__history"><header><div><span><Clock3 size={16}/></span><div><h2>{t('Portfolio Activity History')}</h2><p>{t('Latest setup, opening balance, correction, and trade operations.')}</p></div></div><div className="positions-page__history-edit">{activePortfolio||portfolioList.length===1?<Link to={`/operations/opening-portfolio?edit=${activePortfolio?.id??portfolioList[0].id}`}><Pencil size={14}/>{t('Edit Opening Balance')}</Link>:<><button type="button" aria-expanded={editMenuOpen} onClick={()=>setEditMenuOpen(value=>!value)}><Pencil size={14}/>{t('Edit Opening Balance')}</button>{editMenuOpen?<div>{portfolioList.map(portfolio=><Link key={portfolio.id} to={`/operations/opening-portfolio?edit=${portfolio.id}`}><strong>{portfolio.name}</strong><small>{portfolio.broker_name??t('Broker')}</small></Link>)}</div>:null}</>}</div></header><div>{displayedHistory.map(item=>{const portfolio=activityPortfolio(item);return <Link to={item.activity_url??`/activity/${item.id}`} key={`${item.related_reference}-${item.id}`}><span><strong>{activityTitle(item,language)}</strong><small>{activityDetail(item,language)}{selectedPortfolio==='all'&&portfolio?<em>{portfolio.broker_name?`${portfolio.broker_name} · `:''}{portfolio.name}</em>:null}</small></span><time>{formatDateTime(item.transaction_date)}</time></Link>})}{!displayedHistory.length?<p>{t('No portfolio activity recorded this month.')}</p>:null}</div></section>
  </section>
}
