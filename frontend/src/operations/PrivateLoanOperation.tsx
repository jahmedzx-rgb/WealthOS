import { displayAmountInput, parseAmountInput } from '../utils/amountInput'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import DateInput from '../components/DateInput'
import { useLanguage } from '../context/LanguageContext'
import { useCurrency } from '../context/CurrencyContext'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { createPrivateLoan, getBankAccounts, type BankAccount, type PrivateLoanRequest } from '../services/accountingService'
import './PrivateLoanOperation.css'
import { getAccountProfile } from '../services/accountService'
import { usePrivateLoanDraft } from '../hooks/usePrivateLoanDraft'

export default function PrivateLoanOperation({onBack}:{onBack:()=>void}) {
  const {t}=useLanguage()
  const [userId,setUserId]=useState<number|null>(null),[failed,setFailed]=useState(false)
  useEffect(()=>{let active=true;getAccountProfile().then(profile=>{if(active)setUserId(profile.id)}).catch(()=>{if(active)setFailed(true)});return()=>{active=false}},[])
  if(userId===null)return <p role="status">{t(failed?'Unable to load your draft. Reopen the form.':'Loading…')}</p>
  return <PrivateLoanForm key={userId} userId={userId} onBack={onBack}/>
}

function PrivateLoanForm({onBack,userId}:{onBack:()=>void;userId:number}) {
  const {t,language}=useLanguage()
  const {formatMoney}=useCurrency()
  const {accounts}=usePostingAccounts()
  const [banks,setBanks]=useState<BankAccount[]>([])
  const {draft,update,clear,discard}=usePrivateLoanDraft(userId)
  const {mode,name,lender,principal,extra,paid,date,bank,expense,beneficiary,note,key,dateText}=draft
  const setMode=(v:PrivateLoanRequest['mode'])=>update('mode',v)
  const setName=(v:string)=>update('name',v),setLender=(v:string)=>update('lender',v)
  const setPrincipal=(v:string)=>update('principal',v),setExtra=(v:string)=>update('extra',v),setPaid=(v:string)=>update('paid',v)
  const setDate=(v:string)=>update('date',v),setBank=(v:string)=>update('bank',v),setExpense=(v:string)=>update('expense',v),setBeneficiary=(v:string)=>update('beneficiary',v),setNote=(v:string)=>update('note',v)
  const [status,setStatus]=useState(''),[saved,setSaved]=useState(false),[saving,setSaving]=useState(false)
  const locked=useRef(false)
  const bankOptionLabel=(account: BankAccount)=> {
    const last4=String(account.account_identifier ?? '').replace(/\D/g, '').slice(-4)
    return `${account.bank_name}${last4 ? ` (••••${last4})` : ''}`
  }
  useEffect(()=>{getBankAccounts().then(setBanks).catch(()=>setStatus(t('Unable to load bank accounts.')))},[t])
  const total=Number(principal||0)+Number(extra||0)
  const balance=total-(mode==='OPENING'?Number(paid||0):0)
  const ready=name.trim().length>=2&&lender.trim().length>=2&&date&&Number(principal)>0&&Number(extra)>=0&&Number(paid)>=0&&balance>0&&(mode!=='BANK'||bank)&&(mode!=='DIRECT_EXPENSE'||(expense&&beneficiary.trim()))
  async function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if(!ready||saved||locked.current)return
    locked.current=true;setSaving(true);setStatus('')
    try {
      await createPrivateLoan({name:name.trim(),lender:lender.trim(),mode,principal:Number(principal),agreed_extra:Number(extra),prior_paid:mode==='OPENING'?Number(paid):0,record_date:date,bank_account_id:mode==='BANK'?Number(bank):null,expense_account_code:mode==='DIRECT_EXPENSE'?Number(expense):null,beneficiary:mode==='DIRECT_EXPENSE'?beneficiary.trim():'',note,idempotency_key:key})
      discard();setSaved(true);setStatus(t('Private loan recorded successfully.'))
    } catch(error) {setStatus(t(error instanceof Error?error.message:'Unable to save the loan.'))}
    finally {locked.current=false;setSaving(false)}
  }
  const amount=(label:string,value:string,set:(value:string)=>void,required=false)=><label><span>{t(label)}</span><input required={required} inputMode="decimal" dir="ltr" value={displayAmountInput(value,language)} onChange={e=>set(parseAmountInput(e.target.value))} pattern="[0-9٠-٩۰-۹,٬]+([.٫][0-9٠-٩۰-۹]{1,2})?"/></label>
  return <OperationForm className="private-loan" title={t('Private loan — flexible repayment')} onSubmit={submit} preview={<>
    <div className="standard-operation__preview"><span>{t(mode==='OPENING'?'Opening loan balance':'Total obligation')}</span><strong>{formatMoney(balance,'SAR')}</strong><small>{name||t('Private loan — flexible repayment')}</small></div>
    <div className="income-operation__effects"><p><span>{t('Original financing')}</span><strong>{formatMoney(Number(principal||0),'SAR')}</strong></p><p><span>{t('Agreed additional amount')}</span><strong>{formatMoney(Number(extra||0),'SAR')}</strong></p>{mode==='OPENING'&&<p><span>{t('Paid before opening')}</span><strong>{formatMoney(Number(paid||0),'SAR')}</strong></p>}<p><span>{t('Bank increase')}</span><strong>{formatMoney(mode==='BANK'?Number(principal||0):0,'SAR')}</strong></p></div>
    <div className="income-operation__smart-note"><p>{t('No fixed monthly installment. Record actual payments when made.')}</p></div>
  </>}>
    <label className="scheduled-loan__kind"><span>{t('Loan form')}</span><select value="PRIVATE_FLEXIBLE" disabled={saving} onChange={e=>{if(e.target.value==='SCHEDULED')onBack()}}><option value="SCHEDULED">{t('Scheduled bank loan')}</option><option value="PRIVATE_FLEXIBLE">{t('Private loan — flexible repayment')}</option></select></label>
    <fieldset disabled={saved||saving}>
      <div className="standard-operation__grid">
        <label><span>{t('Loan Name')}</span><input required minLength={2} maxLength={120} value={name} onChange={e=>setName(e.target.value)}/></label>
        <label><span>{t('Lender')}</span><input required minLength={2} maxLength={120} value={lender} onChange={e=>setLender(e.target.value)}/></label>
        <label><span>{t('Recording method')}</span><select value={mode} onChange={e=>setMode(e.target.value as typeof mode)}><option value="OPENING">{t('Existing loan — opening balance')}</option><option value="BANK">{t('New loan — received in bank')}</option><option value="DIRECT_EXPENSE">{t('New loan — direct expense payment')}</option></select></label>
        <label><span>{t(mode==='OPENING'?'Opening Balance Date':'Funding Date')}</span><DateInput key={key} required value={date} initialDraft={dateText} onDraftChange={v=>update('dateText',v)} onChange={e=>setDate(e.target.value)}/></label>
        {amount('Original financing',principal,setPrincipal,true)}
        {amount('Agreed additional amount',extra,setExtra,true)}
        {mode==='OPENING'&&amount('Paid before opening',paid,setPaid,true)}
        {mode==='BANK'&&<label><span>{t('Receiving Bank Account')}</span><select required value={bank} onChange={e=>setBank(e.target.value)}><option value="">{t('Select a bank account')}</option>{banks.filter(b=>b.currency_code==='SAR').map(b=><option key={b.id} value={b.id}>{bankOptionLabel(b)}</option>)}</select></label>}
        {mode==='DIRECT_EXPENSE'&&<><label><span>{t('Beneficiary')}</span><input required maxLength={120} value={beneficiary} onChange={e=>setBeneficiary(e.target.value)}/></label><label><span>{t('Expense account')}</span><select required value={expense} onChange={e=>setExpense(e.target.value)}><option value="">{t('Select Account')}</option>{accounts.filter(a=>a.account_type==='EXPENSE').map(a=><option key={a.code} value={a.code}>{t(a.name)}</option>)}</select></label></>}
        <label><span>{t('Notes')}</span><input maxLength={500} value={note} onChange={e=>setNote(e.target.value)}/></label>
      </div>
    </fieldset>
    <div className="income-operation__smart-note"><p>{t(mode==='OPENING'?'Only the remaining debt is posted against opening equity. Historical totals do not create bank transactions.':mode==='BANK'?'Financing increases the selected bank balance. The agreed additional amount is recorded separately as financing cost.':'Direct expense funding records a new expense without moving bank cash. Do not use it for an asset already recorded.')}</p></div>
    <div className="income-operation__actions"><span role="status">{status||t('Temporary draft only. Closing or reloading this page discards unsaved fields.')}</span><button type="button" disabled={saving} onClick={()=>{if(window.confirm(t('Clear all fields and delete this draft?'))){clear();setSaved(false);setStatus('')}}}>{t('Clear fields')}</button><button type="submit" disabled={!ready||saved||saving}>{t(saved?'Loan recorded':saving?'Processing…':'Record private loan')}</button></div>
  </OperationForm>
}
