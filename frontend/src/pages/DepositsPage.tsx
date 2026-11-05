import { ArrowUpRight, CalendarDays, Landmark, Plus, Sprout } from 'lucide-react'
import { Link } from 'react-router-dom'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useLanguage } from '../context/LanguageContext'
import './DepositsPage.css'
import { formatDisplayPercent } from '../utils/localeFormat'
import { useEffect, useState } from 'react'
import { getDeposits, reconcileDepositReturn, withdrawFromDeposit, type Deposit } from '../services/accountingService'
import { formatDate } from '../utils/dateFormat'
import './InvestingSubpages.css'
import { bankIdentityKey } from '../components/ui/BankIdentity'
import DateInput from '../components/DateInput'

const dateOnly=(value:string)=>new Date(`${value.slice(0,10)}T00:00:00Z`)
const roundMoney=(value:number)=>Math.round((value+Number.EPSILON)*100)/100
const projectedDailyBalance=(item:Deposit,today:string)=>{
  if(item.product_type!=='INCOME_SAVINGS'||item.payout_frequency!=='DAILY')return null
  const from=dateOnly(item.accrual_start_date??item.start_date);const through=dateOnly(today)
  const standard=Number(item.standard_annual_return_rate??item.annual_return_rate)
  const promotional=Number(item.promotional_annual_return_rate??0)
  const promoEnd=item.promotional_rate_end_date?dateOnly(item.promotional_rate_end_date):null
  let balance=Number(item.current_balance);let cursor=from
  while(cursor<through){
    const rate=promotional>0&&promoEnd&&cursor<=promoEnd?promotional:standard
    balance=roundMoney(balance+roundMoney(balance*rate/100/360))
    cursor=new Date(cursor.getTime()+86400000)
  }
  const activeRate=promotional>0&&promoEnd&&through<=promoEnd?promotional:standard
  return{balance,daily:roundMoney(balance*activeRate/100/360)}
}

export default function DepositsPage() {
  const financial = useFinancialSummary()
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const [allDeposits,setAllDeposits]=useState<Deposit[]>([])
  const [reconciling,setReconciling]=useState<number|null>(null)
  const [reconcileDraft,setReconcileDraft]=useState<{item:Deposit;actualReturn:string}|null>(null)
  const [withdrawDraft,setWithdrawDraft]=useState<{item:Deposit;confirmedBalance:string;amount:string;bankId:string;closeDeposit:boolean;transactionDate:string}|null>(null)
  useEffect(()=>{getDeposits().then(setAllDeposits).catch(()=>setAllDeposits([]))},[])
  const deposits = financial.data?.deposits ?? []
  const history=allDeposits.filter(item=>item.status==='CLOSED'||item.status==='RENEWED')
  const today = new Date().toISOString().slice(0,10)
  const activeDeposits = deposits.filter(item=>!item.maturity_date||item.maturity_date>today)
  const total = deposits.reduce((sum, item) => sum + item.current_balance, 0)
  const weightedReturn = total ? deposits.reduce((sum, item) => sum + item.current_balance * item.annual_return_rate, 0) / total : 0
  const nextMaturity = activeDeposits.map(item => item.maturity_date).filter((value): value is string => Boolean(value)).sort()[0]
  const reconcile=async()=>{if(!reconcileDraft)return;const actualReturn=Number(reconcileDraft.actualReturn);if(!Number.isFinite(actualReturn)||actualReturn<=0)return;const item=reconcileDraft.item;setReconciling(item.id);try{await reconcileDepositReturn(item.id,{confirmed_balance:Number((Number(item.current_balance)+actualReturn).toFixed(2)),transaction_date:new Date(`${today}T12:00:00`).toISOString()});setReconcileDraft(null);await financial.refresh()}finally{setReconciling(null)}}
  const withdraw=async()=>{if(!withdrawDraft)return;const amount=Number(withdrawDraft.amount);const confirmed=Number(withdrawDraft.confirmedBalance);if(!withdrawDraft.bankId||amount<=0||confirmed<amount||withdrawDraft.closeDeposit&&amount!==confirmed)return;setReconciling(withdrawDraft.item.id);try{await withdrawFromDeposit(withdrawDraft.item.id,{destination_bank_account_id:Number(withdrawDraft.bankId),confirmed_balance:confirmed,amount,transaction_date:new Date(`${withdrawDraft.transactionDate}T12:00:00`).toISOString(),close_deposit:withdrawDraft.closeDeposit});setWithdrawDraft(null);await Promise.all([financial.refresh(),getDeposits().then(setAllDeposits)])}finally{setReconciling(null)}}

  if (financial.loading) return <main className="deposits-page__state">{t('Loading deposits…')}</main>
  if (financial.error) return <main className="deposits-page__state">{t('Unable to load deposits')}: {t(financial.error)}</main>

  return <section className="deposits-page">
    <PageHeader className="deposits-page__header" eyebrow={t('Savings & Deposits')} title={t('Deposits')} subtitle={t('Review balances, expected returns, payout schedules, and maturity dates.')} icon={Sprout} actions={<Link className="page-header__primary-action" to="/operations/deposit"><Plus size={16}/> {t('Add Deposit')}</Link>}/>

    <div className="deposits-page__metrics">
      <article><span><Landmark size={15}/>{t('Active Deposits')}</span><strong>{activeDeposits.length}</strong><small>{t('Currently Tracked')}</small></article>
      <article><span>{t('Total Balance')}</span><strong><FormattedMoney value={formatMoney(total)}/></strong><small>{t('Posted Deposit Assets')}</small></article>
      <article><span>{t('Weighted Annual Return')}</span><strong>{formatDisplayPercent(weightedReturn,2)}</strong><small>{nextMaturity ? `${t('Next Maturity')} · ${nextMaturity}` : t('No Maturity Date')}</small></article>
    </div>

    <section className="deposits-page__panel">
      <header><div><h2>{t('Deposit Positions')}</h2><p>{t('Every active deposit and savings product recorded in WealthOS.')}</p></div></header>
      <div className="deposits-page__table-head"><span>{t('Deposit')}</span><span>{t('Balance')}</span><span>{t('Return')}</span><span>{t('Maturity')}</span><span>{t('Modify')}</span></div>
      {deposits.length ? deposits.map(item => {const matured=Boolean(item.maturity_date&&item.maturity_date<=today);const projected=projectedDailyBalance(item,today);return <div className={`deposits-page__row${matured?' is-matured':''}`} key={item.id}>
        <span><strong>{item.product_name === 'Monthly Deposit' ? t('Monthly Deposit') : <>{item.product_name}</>}</strong><small>{item.provider_name === 'Wadaie' ? t('Wadaie') : item.provider_name} · {t(item.product_type)}</small></span>
        {projected?<span className="deposits-page__live-balance"><strong><FormattedMoney value={formatMoney(projected.balance,item.currency_code as Currency)}/></strong><small><FormattedMoney value={formatMoney(projected.daily,item.currency_code as Currency)}/> <b>↑</b> <em>{t('per day')}</em></small><button type="button" disabled={reconciling===item.id||projected.balance<=Number(item.current_balance)} onClick={()=>setReconcileDraft({item,actualReturn:(projected.balance-Number(item.current_balance)).toFixed(2)})}>{t('Reconcile')}</button></span>:<strong><FormattedMoney value={formatMoney(item.current_balance, item.currency_code as Currency)}/></strong>}
        <span className="is-positive">{formatDisplayPercent(item.annual_return_rate,2)}</span>
        <span><CalendarDays size={14}/>{item.maturity_date ?? t('Open Ended')}{matured?<small className="deposits-page__maturity-state">{t('Awaiting settlement')}</small>:null}</span>
        <span className="deposits-page__actions"><Link to={`/operations/deposit?edit=${item.id}`}>{t('Edit')}</Link>{item.product_type==='INCOME_SAVINGS'&&projected?<><button type="button" onClick={()=>setWithdrawDraft({item,confirmedBalance:projected.balance.toFixed(2),amount:'',bankId:String(item.income_bank_account_id??''),closeDeposit:false,transactionDate:today})}>{t('Withdraw')}</button><button className="is-disposition" type="button" onClick={()=>setWithdrawDraft({item,confirmedBalance:projected.balance.toFixed(2),amount:projected.balance.toFixed(2),bankId:String(item.income_bank_account_id??''),closeDeposit:true,transactionDate:today})}>{t('Close')}</button></>:null}{item.product_type!=='INCOME_SAVINGS'?<Link className="is-disposition" to={`/operations/break-deposit?deposit=${item.id}`}>{t(matured?'Settle Maturity':'Break')}</Link>:null}</span>
      </div>}) : <div className="deposits-page__empty"><Sprout size={22}/><strong>{t('No Deposits Yet')}</strong><p>{t('Add a deposit to track its balance, return, and maturity.')}</p><Link to="/operations/deposit">{t('Add Deposit')} <ArrowUpRight size={14}/></Link></div>}
    </section>
    {history.length?<section className="deposits-page__panel deposits-page__history"><header><div><h2>{t('Deposit History')}</h2><p>{t('Closed and renewed deposits remain available for review and audit.')}</p></div></header><div className="deposits-page__history-head"><span>{t('Deposit')}</span><span>{t('Principal')}</span><span>{t('Actual Return')}</span><span>{t('Settlement Date')}</span><span>{t('Destination')}</span><span>{t('Status')}</span></div>{history.map(item=>{const bank=financial.data?.bank_accounts.find(account=>account.id===item.settlement_bank_account_id);return <div className="deposits-page__history-row" key={item.id}><span><strong>{item.product_name}</strong><small>{item.provider_name}</small></span><strong><FormattedMoney value={formatMoney(item.principal_amount,item.currency_code as Currency)}/></strong><span className="is-positive"><FormattedMoney value={formatMoney(item.actual_return??0,item.currency_code as Currency)}/></span><span>{item.settled_at?formatDate(item.settled_at):item.maturity_date?formatDate(item.maturity_date):'—'}</span><span>{bank?`${bank.account_name} · ${bank.bank_name} · ${bank.account_identifier}`:item.settlement_action==='REINVEST_ALL'?t('New deposit'):'—'}</span><span className="deposits-page__history-status">{t(item.status==='RENEWED'?'Renewed':'Closed')}</span></div>})}</section>:null}
    {reconcileDraft&&<div className="deposit-reconcile" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)setReconcileDraft(null)}}><section role="dialog" aria-modal="true"><header><div><h2>{t('Reconcile Return')}</h2><p>{reconcileDraft.item.product_name}</p></div></header><label><span>{t('Actual Return')}</span><input autoFocus type="number" min="0.01" step="0.01" value={reconcileDraft.actualReturn} onChange={event=>setReconcileDraft(current=>current?{...current,actualReturn:event.target.value}:current)}/></label><div><span>{t('Confirmed Balance')}</span><strong><FormattedMoney value={formatMoney(Number(reconcileDraft.item.current_balance)+(Number(reconcileDraft.actualReturn)||0),reconcileDraft.item.currency_code as Currency)}/></strong></div><footer><button type="button" onClick={()=>setReconcileDraft(null)}>{t('Cancel')}</button><button type="button" disabled={reconciling===reconcileDraft.item.id||Number(reconcileDraft.actualReturn)<=0} onClick={()=>void reconcile()}>{t('Reconcile')}</button></footer></section></div>}
    {withdrawDraft&&<div className="deposit-reconcile deposit-withdraw" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget)setWithdrawDraft(null)}}><section role="dialog" aria-modal="true"><header><div><h2>{t(withdrawDraft.closeDeposit?'Close Daily Deposit':'Withdraw')}</h2><p>{withdrawDraft.item.product_name}</p></div></header><label><span>{t('Confirmed Provider Balance')}</span><input type="number" min="0.01" step="0.01" value={withdrawDraft.confirmedBalance} onChange={event=>setWithdrawDraft(current=>current?{...current,confirmedBalance:event.target.value,amount:current.closeDeposit?event.target.value:current.amount}:current)}/></label><label><span>{t('Withdrawal Amount')}</span><input autoFocus={!withdrawDraft.closeDeposit} readOnly={withdrawDraft.closeDeposit} type="number" min="0.01" max={withdrawDraft.confirmedBalance} step="0.01" value={withdrawDraft.amount} onChange={event=>setWithdrawDraft(current=>current?{...current,amount:event.target.value}:current)}/></label><label><span>{t('Transaction Date')}</span><DateInput autoFocus={withdrawDraft.closeDeposit} type="date" max={today} value={withdrawDraft.transactionDate} onChange={event=>setWithdrawDraft(current=>current?{...current,transactionDate:event.target.value}:current)}/></label><label><span>{t('Destination Bank Account')}</span><select value={withdrawDraft.bankId} onChange={event=>setWithdrawDraft(current=>current?{...current,bankId:event.target.value}:current)}><option value="">{t('Select Bank Account')}</option>{[...(financial.data?.bank_accounts??[])].filter(bank=>bank.currency_code===withdrawDraft.item.currency_code).sort((a,b)=>bankIdentityKey(a.bank_name).localeCompare(bankIdentityKey(b.bank_name))||a.id-b.id).map(bank=><option value={bank.id} key={bank.id}>{bank.account_name} · {bank.bank_name} · {bank.account_identifier}</option>)}</select></label><div><span>{t('Remaining Deposit Balance')}</span><strong><FormattedMoney value={formatMoney(Math.max(0,Number(withdrawDraft.confirmedBalance)-Number(withdrawDraft.amount||0)),withdrawDraft.item.currency_code as Currency)}/></strong></div><footer><button type="button" onClick={()=>setWithdrawDraft(null)}>{t('Cancel')}</button><button type="button" disabled={reconciling===withdrawDraft.item.id||!withdrawDraft.bankId||!withdrawDraft.transactionDate||Number(withdrawDraft.amount)<=0||Number(withdrawDraft.amount)>Number(withdrawDraft.confirmedBalance)||withdrawDraft.closeDeposit&&Number(withdrawDraft.amount)!==Number(withdrawDraft.confirmedBalance)} onClick={()=>void withdraw()}>{t(withdrawDraft.closeDeposit?'Close Deposit':'Withdraw')}</button></footer></section></div>}
  </section>
}
