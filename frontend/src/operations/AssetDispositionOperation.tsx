import { useMemo, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { breakDeposit, getProperties, sellProperty, type PropertyAsset } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useEffect } from 'react'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayNumber } from '../utils/localeFormat'

const clean=(value:string)=>Number(value.replaceAll(',','')||0)
const display=(value:string)=>value.replace(/[^\d.]/g,'').replace(/\B(?=(\d{3})+(?!\d))/g,',')

export default function AssetDispositionOperation({kind}:{kind:'DEPOSIT'|'PROPERTY'}){
  const[params]=useSearchParams();const financial=useFinancialSummary();const[properties,setProperties]=useState<PropertyAsset[]>([])
  const{t,language}=useLanguage()
  const[id,setId]=useState(params.get(kind==='DEPOSIT'?'deposit':'property')??'');const[paymentMethod,setPaymentMethod]=useState<'BANK_TRANSFER'|'CHEQUE'|'CASH'>('BANK_TRANSFER');const[paymentDestination,setPaymentDestination]=useState<'BANK_ACCOUNT'|'CASH_ON_HAND'>('BANK_ACCOUNT');const[bankId,setBankId]=useState('');const[amount,setAmount]=useState('');const[costs,setCosts]=useState('');const[date,setDate]=useState('');const[reason,setReason]=useState('');const[saving,setSaving]=useState(false);const[message,setMessage]=useState('')
  useEffect(()=>{if(kind==='PROPERTY')getProperties().then(setProperties).catch(()=>setProperties([]))},[kind])
  const deposit=financial.data?.deposits.find(item=>String(item.id)===id);const property=properties.find(item=>String(item.id)===id)
  const banks=financial.data?.bank_accounts??[];const bank=banks.find(item=>String(item.id)===bankId)
  const net=kind==='PROPERTY'?clean(amount)-clean(costs):clean(amount)
  const valid=Boolean(id&&date&&reason.trim().length>=3&&clean(amount)>=0&&(kind==='PROPERTY'?clean(amount)>clean(costs)&&(paymentDestination==='CASH_ON_HAND'||bankId):bankId))
  const title=kind==='DEPOSIT'?t('Break Deposit'):t('Sell Property')
  const impact=useMemo(()=>kind==='DEPOSIT'?t('Closes the deposit and returns the actual settlement to the selected bank account.'):t('Removes the property from active assets and records the sale gain or loss.'),[kind,t])
  async function submit(event:FormEvent){event.preventDefault();if(!valid)return;setSaving(true);setMessage('');try{if(kind==='DEPOSIT'){await breakDeposit(Number(id),{destination_bank_account_id:Number(bankId),amount_received:clean(amount),transaction_date:new Date(date).toISOString(),reason:reason.trim()})}else{await sellProperty(Number(id),{payment_method:paymentMethod,payment_destination:paymentDestination,bank_account_id:paymentDestination==='BANK_ACCOUNT'?Number(bankId):null,sale_amount:clean(amount),selling_costs:clean(costs),transaction_date:new Date(date).toISOString(),description:reason.trim()})}setMessage(kind==='DEPOSIT'?t('Break Deposit Posted Successfully.'):t('Sell Property Posted Successfully.'));await financial.refresh()}catch(error){setMessage(t(error instanceof Error?error.message:kind==='DEPOSIT'?'Unable to break deposit.':'Unable to sell property.'))}finally{setSaving(false)}}
  return <OperationForm title={title} onSubmit={event=>void submit(event)}>
    <div className="standard-operation__grid">
      <label><span>{t(kind==='DEPOSIT'?'Deposit':'Property')}</span><select value={id} onChange={event=>{setId(event.target.value);const selected=financial.data?.deposits.find(item=>String(item.id)===event.target.value);if(selected)setAmount(String(selected.current_balance))}}><option value="">{t(kind==='DEPOSIT'?'Select Deposit':'Select Property')}</option>{kind==='DEPOSIT'?financial.data?.deposits.map(item=><option value={item.id} key={item.id}>{item.product_name==='Monthly Deposit'?t('Monthly Deposit'):item.product_name} · {item.provider_name==='Wadaie'?t('Wadaie'):item.provider_name}</option>):properties.map(item=><option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
      {kind==='PROPERTY'&&<label><span>{t('Payment Method')}</span><select value={paymentMethod} onChange={event=>{const method=event.target.value as typeof paymentMethod;setPaymentMethod(method);if(method==='BANK_TRANSFER')setPaymentDestination('BANK_ACCOUNT');if(method==='CASH')setPaymentDestination('CASH_ON_HAND')}}><option value="BANK_TRANSFER">{t('Bank Transfer')}</option><option value="CHEQUE">{t('Cheque')}</option><option value="CASH">{t('Cash')}</option></select></label>}
      {kind==='PROPERTY'&&paymentMethod==='CHEQUE'&&<label><span>{t('Cheque Proceeds')}</span><select value={paymentDestination} onChange={event=>{setPaymentDestination(event.target.value as typeof paymentDestination);setBankId('')}}><option value="BANK_ACCOUNT">{t('Deposit into a bank account')}</option><option value="CASH_ON_HAND">{t('Keep as cash on hand')}</option></select></label>}
      {(kind==='DEPOSIT'||paymentDestination==='BANK_ACCOUNT')&&<label><span>{t(kind==='PROPERTY'?'Receiving Bank Account':'Destination Bank Account')}</span><select value={bankId} onChange={event=>setBankId(event.target.value)}><option value="">{t('Select Bank Account')}</option>{banks.map(item=><option value={item.id} key={item.id}>{item.account_name} · {item.bank_name}</option>)}</select></label>}
      {kind==='PROPERTY'&&paymentDestination==='CASH_ON_HAND'&&<label><span>{t('Receiving Asset')}</span><input readOnly value={t('Cash On Hand')}/></label>}
      <label><span>{t(kind==='DEPOSIT'?'Amount Received':'Sale Amount')}</span><input inputMode="decimal" value={display(amount)} onChange={event=>setAmount(event.target.value.replaceAll(',',''))}/></label>
      {kind==='PROPERTY'?<label><span>{t('Selling Costs')}</span><input inputMode="decimal" value={display(costs)} onChange={event=>setCosts(event.target.value.replaceAll(',',''))}/></label>:<label><span>{t('Current Deposit Balance')}</span><input readOnly value={formatDisplayNumber(deposit?.current_balance??0,{minimumFractionDigits:2,maximumFractionDigits:2},language)}/></label>}
      <label><span>{t('Transaction Date')}</span><input type="datetime-local" value={date} onChange={event=>setDate(event.target.value)}/></label>
      <label><span>{t('Reason')}</span><input value={reason} onChange={event=>setReason(event.target.value)} placeholder={t('Add a clear audit reference')}/></label>
    </div>
    <div className="income-operation__actions"><span>{message||`${impact}${kind==='PROPERTY'&&property?` ${t('Net proceeds')}: ${formatDisplayNumber(net,{minimumFractionDigits:2,maximumFractionDigits:2},language)}`:''}${bank?` · ${bank.account_name}`:''}`}</span><button type="submit" disabled={!valid||saving}>{saving?t('Posting…'):kind==='DEPOSIT'?t('Post Break Deposit'):title}</button></div>
  </OperationForm>
}
