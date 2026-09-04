import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { createBankAccount, getBankAccount, updateBankAccount } from '../services/accountingService'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'

const localNow=()=>new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)

export default function BankAccountOperation(){
  const{currency,formatMoney}=useCurrency()
  const{t}=useLanguage()
  const[params]=useSearchParams();const editId=params.get('edit');const editMode=Boolean(editId)
  const[form,setForm]=useState({bank_name:'',account_type:'CURRENT',account_name:'',account_identifier:'',currency_code:currency,opening_balance:'',as_of_date:localNow(),is_primary:true})
  const[correctionReason,setCorrectionReason]=useState('')
  const[message,setMessage]=useState('');const[saving,setSaving]=useState(false)
  const balance=Number(form.opening_balance)||0
  const set=(key:string,value:string|boolean)=>setForm(current=>({...current,[key]:value}))
  useEffect(()=>{if(!editId)return;getBankAccount(Number(editId)).then(account=>setForm({bank_name:account.bank_name,account_type:account.account_type,account_name:account.account_name,account_identifier:account.account_identifier,currency_code:account.currency_code as typeof currency,opening_balance:'',as_of_date:localNow(),is_primary:account.is_primary})).catch(error=>setMessage(error instanceof Error?error.message:t('Unable to load bank accounts.')))},[editId,t])
  async function submit(event:FormEvent){event.preventDefault();setMessage('');if(!form.bank_name.trim()){setMessage(t('Bank name is required.'));return}const identifier=form.account_identifier.replace(/[\s-]/g,'').toUpperCase();if(identifier.length<4){setMessage(t('IBAN or account number must contain at least 4 characters.'));return}if(editMode&&correctionReason.trim().length<3){setMessage(t('Correction reason is required.'));return}setSaving(true);try{if(editMode&&editId)await updateBankAccount(Number(editId),{bank_name:form.bank_name,account_type:form.account_type,account_name:form.account_name.trim()||undefined,account_identifier:identifier,correction_reason:correctionReason});else await createBankAccount({...form,account_name:form.account_name.trim()||undefined,account_identifier:identifier,opening_balance:balance,as_of_date:new Date(form.as_of_date).toISOString()});setMessage(t(editMode?'Bank account updated successfully.':'Bank account saved and its opening balance was posted successfully.'));if(!editMode)setForm({bank_name:'',account_type:'CURRENT',account_name:'',account_identifier:'',currency_code:currency,opening_balance:'',as_of_date:localNow(),is_primary:false})}catch(error){setMessage(error instanceof Error?error.message:t('Unable to save the bank account.'))}finally{setSaving(false)}}
  return <OperationForm title={editMode?'Edit Bank Account':'Bank account details'} onSubmit={(event)=>void submit(event)} preview={<><div className="standard-operation__preview"><span>{t(editMode?'Account Number Correction':'Opening Balance')}</span><strong>{editMode?`${form.bank_name} •• ${form.account_identifier.replace(/[\s-]/g,'').slice(-4)}`:formatMoney(balance)}</strong><small>{form.account_name||t('New Bank Account')}</small></div><div className="income-operation__effects"><h4>{t('Account Setup')}</h4><p><span>{t('Bank')}</span><strong>{form.bank_name||t('Not Selected')}</strong></p><p><span>{t('Account Type')}</span><strong>{t(form.account_type)}</strong></p><p><span>{t('Ledger Impact')}</span><strong>{t(editMode?'Same Account Identity':'Balanced Opening Entry')}</strong></p></div></>}>
    <div className="standard-operation__grid">
      <label><span>{t('Bank')}</span><input value={form.bank_name} onChange={e=>set('bank_name',e.target.value)} placeholder={t('Bank name')} required/></label>
      <label><span>{t('Account Type')}</span><select value={form.account_type} onChange={e=>set('account_type',e.target.value)}><option value="CURRENT">{t('Current Account')}</option><option value="SAVINGS">{t('Savings Account')}</option><option value="DEPOSIT">{t('Deposit Account')}</option><option value="DIGITAL">{t('Digital Bank Account')}</option><option value="OTHER">{t('Other')}</option></select></label>
      <label><span>{t('Account Name')} <em className="operation-field__optional">{t('Optional')}</em></span><input value={form.account_name} onChange={e=>set('account_name',e.target.value)} placeholder={t('e.g. Primary Account')}/></label>
      <label><span>{t('IBAN Or Account Number')}</span><input required value={form.account_identifier} onChange={e=>set('account_identifier',e.target.value)} placeholder={t('IBAN or account number')}/></label>
      <label><span>{t('Currency')}</span><input value={form.currency_code} readOnly/></label>
      {!editMode&&<label><span>{t('Opening Balance')}</span><input type="number" step="0.01" value={form.opening_balance} onChange={e=>set('opening_balance',e.target.value)} placeholder="0.00"/></label>}
      {!editMode&&<label><span>{t('Balance Date')}</span><input type="datetime-local" value={form.as_of_date} onChange={e=>set('as_of_date',e.target.value)} required/></label>}
      {editMode&&<label><span>{t('Correction Reason')}</span><input required minLength={3} value={correctionReason} onChange={e=>setCorrectionReason(e.target.value)} placeholder={t('Explain why the account number is being corrected')}/></label>}
      <label><span>{t('Primary Account')}</span><span className="bank-account-operation__primary"><input type="checkbox" checked={form.is_primary} onChange={e=>set('is_primary',e.target.checked)}/>{t('Use This Account Automatically When Funding')}</span></label>
    </div>
    <div className="income-operation__actions"><span>{message||t(editMode?'All previous transactions remain linked to this account. Repeated corrections may reduce accounting record quality.':'The account will be available for balance and liquidity tracking.')}</span><button type="submit" disabled={saving}>{t(saving?'Saving…':editMode?'Save Changes':'Add Bank Account')}</button></div>
  </OperationForm>
}
