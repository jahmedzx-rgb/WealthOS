import { ArrowUpRight, CalendarDays, CircleDollarSign, Coins, Landmark, ReceiptText, TrendingUp } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { getAlternativeInvestments, getFinancialSummary, getJournalEntries, getRentalReminders, getSavingCircles, type JournalEntry } from '../services/accountingService'
import { getDistributionReminders } from '../services/notificationService'
import { formatDate } from '../utils/dateFormat'
import './InvestmentCashFlowsPage.css'
import { useLanguage } from '../context/LanguageContext'

type FlowStatus='UPCOMING'|'AWAITING'|'RECEIVED'
type FlowKind='DISTRIBUTION'|'RENT'|'YIELD'|'PRINCIPAL_RETURN'|'MATURITY'
type CashFlow={id:string;asset:string;provider:string;kind:FlowKind;status:FlowStatus;date:string;gross:number|null;tax:number|null;net:number|null;currency:Currency;frequency:string|null;action:string|null}

const kindLabel:Record<FlowKind,string>={DISTRIBUTION:'Distribution',RENT:'Rental Income',YIELD:'Interest & Yield',PRINCIPAL_RETURN:'Principal Return',MATURITY:'Maturity Proceeds'}
const frequencyParts:Record<string,number>={WEEKLY:52,MONTHLY:12,QUARTERLY:4,SEMI_ANNUAL:2,ANNUAL:1,AT_MATURITY:1,IRREGULAR:1}
const statusOf=(value:string):FlowStatus=>new Date(`${value}T23:59:59`).getTime()<Date.now()?'AWAITING':'UPCOMING'
const nextRecurringDate=(start:string,frequency:string,maturity:string|null)=>{
  if(frequency==='AT_MATURITY')return maturity
  const date=new Date(`${start}T00:00:00`),today=new Date();const months=frequency==='MONTHLY'?1:frequency==='QUARTERLY'?3:frequency==='SEMI_ANNUAL'?6:12
  while(date.getTime()<today.getTime())date.setMonth(date.getMonth()+months)
  return date.toISOString().slice(0,10)
}
const receivedFlow=(entry:JournalEntry,propertyNames:Map<string,string>,rentalFrequencies:Map<string,string>):CashFlow|null=>{
  const line=entry.lines.find(item=>[4200,4300,4400].includes(item.account_code)&&Number(item.credit)>0)
  if(!line)return null
  const accountName=line.account_name.toLowerCase()
  const kind:FlowKind=accountName.includes('rental')?'RENT':accountName.includes('dividend')||accountName.includes('distribution')?'DISTRIBUTION':'YIELD'
  const propertyName=kind==='RENT'&&entry.related_reference?propertyNames.get(entry.related_reference):undefined
  const frequency=kind==='RENT'&&entry.related_reference?rentalFrequencies.get(entry.related_reference)??null:null
  return{id:`received-${entry.id}`,asset:propertyName??entry.description,provider:propertyName?'Investment Property':line.account_name,kind,status:'RECEIVED',date:entry.transaction_date.slice(0,10),gross:Number(line.credit),tax:null,net:Number(line.credit),currency:'SAR',frequency,action:null}
}

export default function InvestmentCashFlowsPage(){
  const{formatMoney}=useCurrency();const{t}=useLanguage();const[flows,setFlows]=useState<CashFlow[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState('');const[tab,setTab]=useState<'ALL'|FlowStatus>('ALL')
  useEffect(()=>{Promise.all([getDistributionReminders(730,true),getRentalReminders(365),getFinancialSummary(),getAlternativeInvestments(),getSavingCircles(),getJournalEntries()]).then(([listed,rentals,financial,alternatives,circles,journals])=>{
    const items:CashFlow[]=[]
    const propertyNames=new Map(financial.properties.map(item=>[item.reference,item.name]))
    const rentalFrequencies=new Map(rentals.map(item=>[item.property_reference,item.frequency]))
    const lastReceivedRent=new Map<string,number>()
    for(const entry of journals){
      if(!entry.related_reference?.startsWith('property:')||lastReceivedRent.has(entry.related_reference))continue
      const rentalLine=entry.lines.find(line=>line.account_name.toLowerCase().includes('rental')&&Number(line.credit)>0)
      if(rentalLine)lastReceivedRent.set(entry.related_reference,Number(rentalLine.credit))
    }
    for(const item of listed)items.push({id:`position-${item.position_id}`,asset:`${item.symbol} · ${item.name}`,provider:item.portfolio_name,kind:'DISTRIBUTION',status:statusOf(item.distribution_date),date:item.distribution_date,gross:item.expected_amount,tax:item.expected_tax_amount,net:item.expected_net_amount,currency:item.currency_code as Currency,frequency:item.frequency,action:`/operations/income?type=${item.name.toLowerCase().includes('reit')||item.name.toLowerCase().includes('fund')?'FUND_DISTRIBUTION':'DIVIDEND'}&asset=${encodeURIComponent(`${item.symbol} · ${item.name}`)}`})
    for(const item of rentals){const amount=lastReceivedRent.get(item.property_reference)??Number(item.expected_amount);items.push({id:`rental-${item.id}`,asset:item.property_name,provider:'Investment Property',kind:'RENT',status:statusOf(item.next_due_date),date:item.next_due_date,gross:amount,tax:0,net:amount,currency:'SAR',frequency:item.frequency,action:`/operations/income?type=RENTAL&property=${encodeURIComponent(item.property_reference)}`})}
    for(const item of financial.deposits){const date=nextRecurringDate(item.start_date,item.payout_frequency,item.maturity_date);if(!date)continue;const gross=Number(item.current_balance)*Number(item.annual_return_rate)/100/(frequencyParts[item.payout_frequency]??1);items.push({id:`deposit-yield-${item.id}`,asset:item.product_name,provider:item.provider_name,kind:'YIELD',status:statusOf(date),date,gross,tax:0,net:gross,currency:item.currency_code as Currency,frequency:item.payout_frequency,action:`/operations/income?type=INTEREST&asset=${encodeURIComponent(`${item.product_name} · ${item.provider_name}`)}`});if(item.payout_frequency==='AT_MATURITY')items.push({id:`deposit-principal-${item.id}`,asset:item.product_name,provider:item.provider_name,kind:'PRINCIPAL_RETURN',status:statusOf(date),date,gross:Number(item.current_balance),tax:0,net:Number(item.current_balance),currency:item.currency_code as Currency,frequency:'AT_MATURITY',action:'/investing/deposits'})}
    for(const item of alternatives){const date=item.next_distribution_date??item.maturity_date;if(!date)continue;const maturity=!item.next_distribution_date&&Boolean(item.maturity_date);const gross=Number(item.current_value)*Number(item.expected_annual_return)/100/(frequencyParts[item.distribution_frequency??'ANNUAL']??1);items.push({id:`alternative-yield-${item.id}`,asset:item.investment_name,provider:item.platform_name,kind:'YIELD',status:statusOf(date),date,gross,tax:null,net:gross,currency:item.currency_code as Currency,frequency:item.distribution_frequency,action:'/operations/income?type=P2P_YIELD'});if(maturity)items.push({id:`alternative-principal-${item.id}`,asset:item.investment_name,provider:item.platform_name,kind:'PRINCIPAL_RETURN',status:statusOf(date),date,gross:Number(item.current_value),tax:0,net:Number(item.current_value),currency:item.currency_code as Currency,frequency:'AT_MATURITY',action:'/investing/alternative-investments'})}
    for(const item of circles){if(!item.payout_date)continue;const gross=Number(item.installment_amount)*Number(item.total_installments);items.push({id:`circle-${item.id}`,asset:item.circle_name,provider:item.platform_name,kind:'PRINCIPAL_RETURN',status:statusOf(item.payout_date),date:item.payout_date,gross,tax:0,net:gross,currency:'SAR',frequency:null,action:'/investing/saving-circles'})}
    for(const entry of journals){const received=receivedFlow(entry,propertyNames,rentalFrequencies);if(received)items.push(received)}
    setFlows(items.sort((a,b)=>a.date.localeCompare(b.date)))
  }).catch(reason=>setError(t(reason instanceof Error?reason.message:'Unable to load investment cash flows.'))).finally(()=>setLoading(false))},[t])
  const visible=useMemo(()=>tab==='ALL'?flows:flows.filter(item=>item.status===tab),[flows,tab]);const received=flows.filter(item=>item.status==='RECEIVED');const upcoming=flows.filter(item=>item.status==='UPCOMING');const awaiting=flows.filter(item=>item.status==='AWAITING');const receivedTotal=received.reduce((sum,item)=>sum+(item.net??0),0);const expectedTotal=[...upcoming,...awaiting].reduce((sum,item)=>sum+(item.net??0),0)
  return <section className="cash-flows-page"><PageHeader eyebrow={t('Investment Income')} title={t('Investment Cash Flows')} subtitle={t('Distributions, rent, yield, principal returns, and maturity proceeds in one place.')} icon={Coins}/><div className="cash-flows-page__metrics"><article><span>{t('Expected Net Cash')}</span><strong><FormattedMoney value={formatMoney(expectedTotal)}/></strong><small>{upcoming.length} {t('upcoming events')}</small></article><article><span>{t('Awaiting Receipt')}</span><strong>{awaiting.length}</strong><small>{t('Due dates already reached')}</small></article><article><span>{t('Received')}</span><strong><FormattedMoney value={formatMoney(receivedTotal)}/></strong><small>{t('Posted investment income')}</small></article></div><nav className="cash-flows-page__tabs">{(['ALL','UPCOMING','AWAITING','RECEIVED'] as const).map(value=><button className={tab===value?'is-active':''} onClick={()=>setTab(value)} key={value}>{t(value==='ALL'?'All Cash Flows':value.replace('_',' '))}</button>)}</nav>{loading?<div className="cash-flows-page__state">{t('Loading investment cash flows…')}</div>:error?<div className="cash-flows-page__state is-error">{error}</div>:<section className="cash-flows-page__panel"><div className="cash-flows-page__head"><span>{t('Asset')}</span><span>{t('Cash Flow')}</span><span>{t('Date')}</span><span>{t('Gross')}</span><span>{t('Tax')}</span><span>{t('Net')}</span><span>{t('Status')}</span></div>{visible.length?visible.map(item=><div className="cash-flows-page__row" key={item.id}><span><strong>{item.asset}</strong><small>{item.provider==='Investment Property'?t(item.provider):item.provider}</small></span><span className="cash-flows-page__kind">{item.kind==='RENT'?<Landmark size={14}/>:item.kind==='PRINCIPAL_RETURN'?<CircleDollarSign size={14}/>:<TrendingUp size={14}/>}<span><strong>{t(kindLabel[item.kind])}</strong><small>{t(item.frequency?.replaceAll('_',' ')??'One-time')}</small></span></span><span><CalendarDays size={13}/>{formatDate(item.date)}</span><strong>{item.gross==null?'—':formatMoney(item.gross,item.currency)}</strong><span>{item.tax==null?'—':formatMoney(item.tax,item.currency)}</span><strong>{item.net==null?'—':formatMoney(item.net,item.currency)}</strong><span className={`cash-flows-page__status is-${item.status.toLowerCase()}`}>{t(item.status==='AWAITING'?'Awaiting Receipt':item.status==='RECEIVED'?'Received':'Upcoming')}{item.action?<Link to={item.action}>{t(item.kind==='PRINCIPAL_RETURN'?'Review':'Record Receipt')} <ArrowUpRight size={12}/></Link>:null}</span></div>):<div className="cash-flows-page__empty"><ReceiptText size={21}/><strong>{t('No cash flows in this view')}</strong><span>{t('Upcoming and posted investment proceeds will appear here.')}</span></div>}</section>}<div className="cash-flows-page__note"><Coins size={16}/><span><strong>{t('Accounting distinction')}</strong>{t('Distributions, rent, and yield are income. Principal returns and saving-circle payouts reduce the related asset instead of creating income.')}</span></div></section>
}
