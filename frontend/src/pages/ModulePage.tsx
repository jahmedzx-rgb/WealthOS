import { ArrowUpRight, BarChart3, Building2, CreditCard, FileBarChart, Landmark, Plus, ReceiptText, Settings, ShieldCheck, WalletCards } from 'lucide-react'
import { useEffect, useState, type ElementType } from 'react'
import { Link } from 'react-router-dom'
import './ModulePage.css'
import './ModulePageActions.css'
import PageHeader from '../components/ui/PageHeader'
import './PageHeaderNavigation.css'
import { updateMarketPrices } from '../services/portfolioService'
import { usePortfolio } from '../hooks/usePortfolio'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { supportedCurrencies, useCurrency, type Currency } from '../context/CurrencyContext'
import WealthAllocationOverview from '../components/dashboard/WealthAllocationOverview'
import FormattedMoney from '../components/ui/FormattedMoney'
import { formatDate } from '../utils/dateFormat'
import { closeCreditCard, getBankAccounts, getProperties, type BankAccount, type PropertyAsset } from '../services/accountingService'
import PropertyModifyActions from '../components/investing/PropertyModifyActions'
import FairValueEditor from '../components/investing/FairValueEditor'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayInteger, formatDisplayNumber, formatDisplayPercent } from '../utils/localeFormat'

type ModuleKey = 'investing' | 'banking' | 'cards' | 'properties' | 'accounting' | 'reporting' | 'settings'
type Config = { eyebrow: string; title: string; subtitle: string; icon: ElementType; accent: string; metrics: [string,string,string][]; actions: [string,string][]; rows: [string,string,string][] }
const propertyUsageLabel=(usage:PropertyAsset['usage'])=>usage==='UNSPECIFIED'?'Use Not Set':usage.toLowerCase().replaceAll('_',' ').replace(/\b\w/g,letter=>letter.toUpperCase())

const configs: Record<ModuleKey, Config> = {
  investing: { eyebrow:'Portfolio management', title:'Investing', subtitle:'Monitor portfolios, positions, performance, and investment income.', icon:BarChart3, accent:'blue', metrics:[], actions:[['Trade securities','Buy or sell listed investments'],['Add deposit','Fund a deposit or income-producing savings product'],['Add broker','Register a broker for investment trades'],['Update prices','Refresh portfolio valuations']], rows:[] },
  banking: { eyebrow:'Liquidity management', title:'Bank Accounts', subtitle:'A consolidated view of cash, bank balances, and liquidity.', icon:Landmark, accent:'teal', metrics:[], actions:[['Add bank account','Connect or create an account'],['Transfer funds','Move money between accounts'],['Reconcile account','Review unmatched entries']], rows:[] },
  cards: { eyebrow:'Credit management', title:'Credit Cards', subtitle:'Track balances, utilization, statements, and upcoming payments.', icon:CreditCard, accent:'violet', metrics:[], actions:[['Pay credit card','Record a card payment'],['Add credit card','Connect a new card'],['Review statement','Reconcile recent charges']], rows:[] },
  properties: { eyebrow:'Real estate wealth', title:'Properties', subtitle:'Manage property values, income, expenses, and financing.', icon:Building2, accent:'gold', metrics:[['Property Value','—','No Posted Properties'],['Net Rental Income','—','Current Month'],['Property Financing','—','Posted Mortgage Balance']], actions:[['Record property purchase','Post the acquisition to the ledger'],['Record rental income','Link income to a property'],['Manage valuations','Use Edit on a property to post a protected value adjustment']], rows:[] },
  accounting: { eyebrow:'Financial records', title:'Accounting', subtitle:'Review the ledger, journals, income, expenses, and reconciliation.', icon:ReceiptText, accent:'navy', metrics:[], actions:[['Record income','Create an income journal'],['Record expense','Create an expense journal'],['Manual journal','Post an advanced entry']], rows:[] },
  reporting: { eyebrow:'Financial intelligence', title:'Reporting', subtitle:'Turn your wealth data into clear statements and performance insights.', icon:FileBarChart, accent:'blue', metrics:[], actions:[['Balance sheet','Assets, liabilities, and equity'],['Cash flow statement','Inflows and outflows by activity'],['Performance report','Returns, income, and attribution']], rows:[] },
  settings: { eyebrow:'Workspace control', title:'Settings', subtitle:'Configure your profile, preferences, currencies, and data connections.', icon:Settings, accent:'slate', metrics:[], actions:[['Profile & entities','Personal and ownership details'],['Currencies & formats','Display and conversion preferences'],['Connections','Banks, brokers, and providers']], rows:[] },
}

export default function ModulePage({ module }: { module: ModuleKey }) {
  const config = configs[module]; const Icon = config.icon
  const portfolio = usePortfolio('consolidated')
  const refreshPortfolio = portfolio.refresh
  const financial = useFinancialSummary()
  const { formatMoney } = useCurrency()
  const {t,language}=useLanguage()
  const [priceUpdateStatus, setPriceUpdateStatus] = useState('')
  const [isUpdatingPrices, setIsUpdatingPrices] = useState(false)
  const [cardActionStatus, setCardActionStatus] = useState('')
  const [properties,setProperties]=useState<PropertyAsset[]>([])
  const [bankAccounts,setBankAccounts]=useState<BankAccount[]>([])
  useEffect(()=>{if(module==='properties'||module==='investing')getProperties().then(setProperties).catch(()=>setProperties([]))},[module])
  useEffect(()=>{if(module==='banking')getBankAccounts().then(setBankAccounts).catch(()=>setBankAccounts([]))},[module])
  useEffect(()=>{if(module!=='investing')return;let active=true;updateMarketPrices().then(()=>{if(active)return refreshPortfolio()}).catch(()=>undefined);return()=>{active=false}},[module,refreshPortfolio])

  const actionRoute = (name: string) => {
    if (name === 'Trade securities') return '/operations/trade'
    if (name === 'Add broker') return '/operations/add-broker'
    if (name === 'Add deposit') return '/operations/deposit'
    if (name === 'Add investment') return '/operations/trade'
    if (name === 'Add bank account') return '/operations/bank-account'
    if (name === 'Transfer funds') return '/operations/transfer'
    if (name === 'Reconcile account') return '/accounting/reconciliation'
    if (name === 'Record income') return '/operations/income'
    if (name === 'Record expense') return '/operations/expense'
    if (name === 'Pay credit card') return '/operations/card-payment'
    if (name === 'Add credit card') return '/operations/credit-card-account'
    if (name === 'Review statement') return '/accounting/reconciliation'
    if (name === 'Record property purchase') return '/operations/property'
    if (name === 'Record rental income') return '/operations/income'
    if (name === 'Manage valuations') return '/properties'
    return null
  }

  const overviewRoute = module === 'banking' ? '/accounting/ledger' : module === 'cards' ? '/accounting/reconciliation' : module === 'properties' ? '/accounting' : null
  const addRoute = module === 'banking' ? '/operations/bank-account' : module === 'cards' ? '/operations/credit-card-account' : module === 'properties' ? '/operations/property' : null

  const propertyBalance = financial.data?.asset_breakdown.find((item)=>item.code===1210)?.balance??0
  const rentalIncome = financial.data?.income_breakdown.filter(item=>item.code===4200||item.name.toLowerCase().includes('rental')).reduce((sum,item)=>sum+item.balance,0)??0
  const portfolioCurrency=(portfolio.data?.portfolio.base_currency_code??'SAR') as Currency
  const portfolioSarRate=supportedCurrencies.find(item=>item.code===portfolioCurrency)?.sarRate??1
  const marketValueSar=(portfolio.data?.summary.market_value??0)*portfolioSarRate
  const ledgerMarketBook=financial.data?.asset_breakdown.filter(item=>item.code>=1310&&item.code<=1390).reduce((sum,item)=>sum+item.balance,0)??0
  const nonMarketAssets=(financial.data?.total_assets??0)-ledgerMarketBook
  const totalWealthAssets=nonMarketAssets+marketValueSar
  const unavailableMetrics:[string,string,string][]= [['Current Data','—',financial.loading||portfolio.loading?'Loading Posted Information':'Data Unavailable']]
  const liveMetrics: [string,string,string][] = module==='investing'&&portfolio.data&&financial.data ? [['Total Wealth Assets',formatMoney(totalWealthAssets),'Market Value Plus Non-Market Assets'],['Market Investments',formatMoney(portfolio.data.summary.market_value,portfolioCurrency),'Current Market Value'],['Other Assets',formatMoney(nonMarketAssets),'Cash, Property, Deposits And More']] : module==='banking'&&financial.data ? [['Bank Balances',formatMoney(financial.data.bank_account_summary.total_balance),`${formatDisplayInteger(financial.data.bank_account_summary.accounts_count,language)} ${t('Posted Accounts')}`],['Monthly Inflow',formatMoney(financial.data.bank_account_summary.monthly_inflow),'Current Month'],['Monthly Outflow',formatMoney(financial.data.bank_account_summary.monthly_outflow),'Current Month']] : module==='cards'&&financial.data ? [[t('Credit Used'),formatMoney(financial.data.credit_card_summary.used),`${formatDisplayInteger(financial.data.credit_card_summary.cards_count,language)} ${t('Posted Cards')}`],[t('Available Credit'),formatMoney(financial.data.credit_card_summary.available),`${t('Of')} ${formatMoney(financial.data.credit_card_summary.total_limit)} ${t('Total Limit')}`],[t('Utilization'),formatDisplayPercent(financial.data.credit_card_summary.utilization,1,language),`${formatMoney(financial.data.credit_card_summary.monthly_obligation)} ${t('Monthly DBR Obligation')}`]] : module==='properties'&&financial.data ? [['Property Value',formatMoney(propertyBalance),'Posted Ledger Value'],['Net Rental Income',formatMoney(rentalIncome),'Current Month · Rental Accounts Only'],['Property Financing',formatMoney(financial.data.liability_breakdown.filter(item=>item.code===2210).reduce((sum,item)=>sum+item.balance,0)),'Posted Mortgage Balance']] : unavailableMetrics
  const liveRows: [string,string,string][] = module==='investing'&&portfolio.data&&financial.data ? [...portfolio.data.positions.map(item=>[`${item.symbol} · ${item.name}`,formatMoney(item.market_value,item.currency_code as Currency),item.next_distribution_date?`Distribution ${formatDate(item.next_distribution_date)}`:`${formatDisplayNumber(item.quantity,undefined,language)} Units`] as [string,string,string]),...financial.data.deposits.map(item=>[`${item.product_name} · ${item.provider_name}`,formatMoney(item.current_balance,item.currency_code as Currency),item.maturity_date?`Matures ${formatDate(item.maturity_date)}`:item.payout_frequency.replaceAll('_',' ')] as [string,string,string])] : module==='banking'&&financial.data ? financial.data.bank_accounts.map(item=>[item.display_name??`${item.bank_name} ${item.account_identifier}`,formatMoney(item.current_balance),item.account_type]) : module==='cards'&&financial.data ? financial.data.credit_cards.map(card=>[`${card.card_name} •• ${card.last4}`,formatMoney(card.current_balance),card.payment_due_day?`Payment Due · Day ${formatDisplayInteger(card.payment_due_day,language)}`:`Billing Dates Not Set`]) : module==='properties'&&financial.data ? financial.data.asset_breakdown.filter(item=>item.code===1210).map(item=>[item.name,formatMoney(item.balance),`Ledger ${formatDisplayInteger(item.code,language)}`]) : []

  async function handlePriceUpdate() {
    setIsUpdatingPrices(true)
    setPriceUpdateStatus('')
    try {
      const result = await updateMarketPrices()
      setPriceUpdateStatus(`${result.updated_count} market prices updated`)
    } catch (error) {
      setPriceUpdateStatus(error instanceof Error ? error.message : 'Unable to update market prices.')
    } finally {
      setIsUpdatingPrices(false)
    }
  }

  async function handleRemoveCard(cardId:number, balance:number, cardName:string) {
    if(balance>0){setCardActionStatus(`${cardName} ${t('cannot be removed yet. Pay the full outstanding balance of')} ${formatMoney(balance)} ${t('first.')}`);return}
    if(!window.confirm(`${t('Remove')} ${cardName} ${t('from active credit cards? Its transaction history will be retained.')}`))return
    try{await closeCreditCard(cardId);setCardActionStatus(`${cardName} ${t('was closed successfully.')}`);await financial.refresh()}
    catch(error){setCardActionStatus(t(error instanceof Error?error.message:'Unable to remove this credit card.'))}
  }

  return <section className={`module-page module-page--${module} module-page--${config.accent}`}>
    <PageHeader className="module-page__header" title={t(config.title)} subtitle={t(config.subtitle)} icon={Icon} actions={addRoute ? <Link className="page-header__primary-action" to={addRoute}><Plus size={16}/> {t('Add New')}</Link> : null}/>
    <div className="module-page__metrics">{liveMetrics.map(([label,value,note])=><article key={label}><span>{t(label)}</span><strong><FormattedMoney value={value}/></strong><small>{t(note)}</small></article>)}</div>
    {module==='investing'&&portfolio.data&&financial.data?<WealthAllocationOverview allocation={portfolio.data.allocation_summary} positions={portfolio.data.positions} totalValue={portfolio.data.summary.market_value} portfolioCurrency={portfolioCurrency} assetBreakdown={financial.data.asset_breakdown} deposits={financial.data.deposits} realEstateReturn={financial.data.real_estate_return} showLink={false}/>:null}
    <div className="module-page__body"><section className="module-page__panel">
      <div className="module-page__panel-title"><div><h2>{t(module==='settings'?'Workspace Overview':'Current Overview')}</h2><p>{t('Latest Posted Information')}</p></div><nav className="module-page__reference-links">{module==='investing'?<><Link className="module-page__view-link" to="/investing/positions">{t('Stocks')} <ArrowUpRight size={14}/></Link><Link className="module-page__view-link" to="/properties">{t('Properties')} <ArrowUpRight size={14}/></Link><Link className="module-page__view-link" to="/investing/deposits">{t('Deposits')} <ArrowUpRight size={14}/></Link><Link className="module-page__view-link" to="/investing/alternative-investments">{t('Alternatives')} <ArrowUpRight size={14}/></Link><Link className="module-page__view-link" to="/investing/saving-circles">{t('Saving Circles')} <ArrowUpRight size={14}/></Link><Link className="module-page__view-link" to="/investing/cash">{t('Cash')} <ArrowUpRight size={14}/></Link></>:null}{overviewRoute?<Link className="module-page__view-link" to={overviewRoute}>{t(module==='banking'?'View Activity':'View All')} <ArrowUpRight size={14}/></Link>:null}</nav></div>
      {module==='cards'&&cardActionStatus?<p className="module-page__card-status">{cardActionStatus}</p>:null}
      <div className="module-page__table">
        {module==='investing'?<div className="module-page__asset-head"><span>{t('Asset Type')}</span><span>{t('Modify')}</span><span>{t('Amount')}</span><span>{t('Comments')}</span></div>:null}
      {module==='banking'&&bankAccounts.length?bankAccounts.map(item=><div className="module-page__card-row" key={`bank-${item.id}`}><span className="module-page__card-name"><span>{item.display_name??`${item.bank_name} ${item.account_identifier}`}</span><span className="module-page__card-actions"><Link className="module-page__row-edit" to={`/operations/bank-account?edit=${item.id}`}>{t('Edit')}</Link><Link className="module-page__row-edit" to={`/operations/bank-opening-balance?account=${item.id}`}>{t(item.has_opening_balance?'Correct Opening Balance':'Add Opening Balance')}</Link></span></span><strong><FormattedMoney value={formatMoney(item.current_balance,item.currency_code as Currency)}/></strong><small>{t(item.account_type)}</small></div>)
        :module==='properties'&&properties.length?properties.map(item=><div className="module-page__card-row" key={`property-${item.id}`}><span className="module-page__card-name"><span>{item.name}</span><PropertyModifyActions propertyId={item.id}/></span><strong><FormattedMoney value={formatMoney(item.current_value)}/></strong><small>{t(propertyUsageLabel(item.usage))}</small></div>)
        :module==='cards'&&financial.data?financial.data.credit_cards.map(card=><div className="module-page__card-row" key={card.id}><span className="module-page__card-name"><span>{card.card_name} •• {card.last4}</span><span className="module-page__card-actions"><Link className="module-page__row-edit" to={`/operations/credit-card-account?edit=${card.id}`}>{t('Edit')}</Link><button className="module-page__row-remove" type="button" onClick={()=>void handleRemoveCard(card.id,card.current_balance,card.card_name)}>{t('Remove')}</button></span></span><strong><FormattedMoney value={formatMoney(card.current_balance)}/></strong><small>{card.payment_due_day?`${t('Payment Due')} · ${t('Day')} ${formatDisplayInteger(card.payment_due_day,language)}`:t('Billing Dates Not Set')}</small></div>)
        :module==='investing'&&financial.data?<>{financial.data.deposits.map(item=><div className="module-page__asset-row" key={`deposit-${item.id}`}><span>{item.product_name} · {item.provider_name}</span><span className="module-page__modify-actions"><Link className="module-page__row-edit" to={`/operations/deposit?edit=${item.id}`}>{t('Edit')}</Link><Link className="module-page__row-edit is-disposition" to={`/operations/break-deposit?deposit=${item.id}`}>{t('Break')}</Link></span><strong><FormattedMoney value={formatMoney(item.current_balance,item.currency_code as Currency)}/></strong><small>{item.maturity_date?`${t('Matures')} ${formatDate(item.maturity_date)}`:t(item.payout_frequency.replaceAll('_',' '))}</small></div>)}{properties.map(item=><div className="module-page__asset-row" key={`property-${item.id}`}><span>{item.name}</span><PropertyModifyActions propertyId={item.id}/><strong><FormattedMoney value={formatMoney(item.current_value)}/></strong><small>{t('Property')} · {t(propertyUsageLabel(item.usage))}</small></div>)}{[...portfolio.data?.positions??[]].map(item=><div className="module-page__asset-row" key={`position-${item.security_id}`}><span>{item.security_type==='REIT'?item.name.replace(/\s+Fund$/i,''):item.name} · {formatDisplayNumber(item.quantity,undefined,language)} {t('Units')}</span><span className="module-page__modify-actions"><Link className="module-page__row-edit" to={`/operations/trade?portfolio=${item.portfolio_id}&security=${item.security_id}&side=BUY`}>{t('Buy')}</Link><Link className="module-page__row-edit is-disposition" to={`/operations/trade?portfolio=${item.portfolio_id}&security=${item.security_id}&side=SELL`}>{t('Sell')}</Link></span><strong><FormattedMoney value={formatMoney(item.market_value,item.currency_code as Currency)}/></strong><small><FairValueEditor portfolioId={item.portfolio_id!} securityId={item.security_id} value={item.fair_value} currency={item.currency_code as Currency} onSaved={()=>void refreshPortfolio()}/></small></div>)}</>
        :liveRows.length?liveRows.map(([name,value,note])=><div key={`${name}-${note}`}><span>{name}</span><strong><FormattedMoney value={value}/></strong><small>{note}</small></div>)
        :<div><span>{t('No Posted Records')}</span><strong>—</strong><small>{t('Use Add New to begin')}</small></div>}
      </div>
    </section>
    <aside className="module-page__panel"><div className="module-page__panel-title"><div><h2>{t('Quick actions')}</h2><p>{t('Common tasks')}</p></div><ShieldCheck size={17}/></div><div className="module-page__actions">{config.actions.map(([name,note]) => {
      const route = actionRoute(name)
      const content = <><span><WalletCards size={16}/></span><div><strong>{t(name)}</strong><small>{t(name === 'Update prices' && priceUpdateStatus ? priceUpdateStatus : note)}</small></div><ArrowUpRight size={14}/></>
      if (name === 'Update prices') return <button type="button" key={name} onClick={handlePriceUpdate} disabled={isUpdatingPrices}>{content}</button>
      return route ? <Link to={route} key={name}>{content}</Link> : <button type="button" key={name} disabled>{content}</button>
    })}</div></aside></div>
  </section>
}
