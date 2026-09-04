import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { getBankAccounts, setBankOpeningBalance, type BankAccount } from '../services/accountingService'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'

const localNow=()=>new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)

export default function BankOpeningBalanceOperation(){
  const[params]=useSearchParams();const accountId=Number(params.get('account'))
  const{formatMoney}=useCurrency();const{t}=useLanguage()
  const[account,setAccount]=useState<BankAccount|null>(null);const[loading,setLoading]=useState(true)
  const[target,setTarget]=useState('');const[openingDate,setOpeningDate]=useState(localNow())
  const[adjustmentDate,setAdjustmentDate]=useState(localNow());const[reason,setReason]=useState('')
  const[saving,setSaving]=useState(false);const[message,setMessage]=useState('')
  useEffect(()=>{getBankAccounts().then(items=>{const selected=items.find(item=>item.id===accountId)??null;setAccount(selected);if(selected){setTarget(String(selected.opening_balance??0));if(selected.opening_balance_date)setOpeningDate(selected.opening_balance_date.slice(0,16))}else setMessage(t('Bank account not found.'))}).catch(()=>setMessage(t('Unable to load bank accounts.'))).finally(()=>setLoading(false))},[accountId,t])
  const corrected=Number(target)||0;const previous=Number(account?.opening_balance??0);const difference=corrected-previous
  const projected=Number(account?.current_balance??0)+difference
  const title=account?.has_opening_balance?'Correct Opening Balance':'Add Opening Balance'
  const valid=Boolean(account&&corrected>=0&&difference!==0&&reason.trim().length>=3&&openingDate&&adjustmentDate)
  const differenceLabel=useMemo(()=>`${difference>=0?'+':''}${formatMoney(difference,(account?.currency_code??'SAR') as Currency)}`,[difference,formatMoney,account?.currency_code])
  async function submit(event:FormEvent){event.preventDefault();if(!valid||!account)return;setSaving(true);setMessage('');try{const result=await setBankOpeningBalance(account.id,{corrected_opening_balance:corrected,opening_date:new Date(openingDate).toISOString(),adjustment_date:new Date(adjustmentDate).toISOString(),reason:reason.trim()});setAccount(current=>current?{...current,has_opening_balance:true,opening_balance:Number(result.corrected_opening_balance),opening_balance_date:current.opening_balance_date??result.posting_date,current_balance:Number(result.current_balance)}:current);setTarget(String(result.corrected_opening_balance));setMessage(t(result.prior_period_adjustment?'Opening balance corrected as a prior-period adjustment.':'Opening balance saved successfully.'))}catch(error){setMessage(error instanceof Error?error.message:t('Unable to save the opening balance.'))}finally{setSaving(false)}}
  return <OperationForm title={title} onSubmit={event=>void submit(event)} preview={<><div className="standard-operation__preview"><span>{t('Correct Opening Balance')}</span><strong>{account?formatMoney(corrected,account.currency_code as Currency):'—'}</strong><small>{account?.account_name??t('Select a bank account')}</small></div><div className="income-operation__effects"><h4>{t('Accounting impact')}</h4><p><span>{t('Previous opening balance')}</span><strong>{account?formatMoney(previous,account.currency_code as Currency):'—'}</strong></p><p><span>{t('Difference to post')}</span><strong>{account?differenceLabel:'—'}</strong></p><p><span>{t('Current balance after correction')}</span><strong>{account?formatMoney(projected,account.currency_code as Currency):'—'}</strong></p></div></>}>
    {loading?<p>{t('Loading bank account…')}</p>:account?<div className="standard-operation__grid">
      <label><span>{t('Bank Account')}</span><input value={`${account.account_name} · ${account.bank_name}`} readOnly/></label>
      <label><span>{t('Current opening balance')}</span><input value={formatMoney(previous,account.currency_code as Currency)} readOnly/></label>
      <label><span>{t('Correct opening balance')}</span><input min="0" step="0.01" type="number" value={target} onChange={event=>setTarget(event.target.value)} required/></label>
      <label><span>{t(account.has_opening_balance?'Original opening date':'Opening balance date')}</span><input type="datetime-local" value={openingDate} onChange={event=>setOpeningDate(event.target.value)} readOnly={account.has_opening_balance} required/></label>
      <label><span>{t('Correction date')}</span><input type="datetime-local" value={adjustmentDate} onChange={event=>setAdjustmentDate(event.target.value)} required/></label>
      <label><span>{t('Reason')}</span><input value={reason} onChange={event=>setReason(event.target.value)} placeholder={t('Explain why the opening balance is being changed')} required minLength={3}/></label>
    </div>:null}
    <div className="income-operation__actions"><span>{message||t(account?.has_opening_balance?'Only the difference will be posted; later transactions will remain unchanged.':'Use this only for money that existed before WealthOS.')}</span><button type="submit" disabled={saving||!valid}>{t(saving?'Saving…':title)}</button></div>
  </OperationForm>
}
