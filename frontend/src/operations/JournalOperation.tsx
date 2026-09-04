import { useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { postJournalEntry } from '../services/accountingService'
import { useLanguage } from '../context/LanguageContext'

export default function JournalOperation({ expense = false }: { expense?: boolean }) {
  const {t}=useLanguage()
  const {accounts,loading,error}=usePostingAccounts()
  const [debitCode,setDebitCode]=useState('')
  const [creditCode,setCreditCode]=useState('')
  const [amount,setAmount]=useState('')
  const [date,setDate]=useState('')
  const [description,setDescription]=useState(expense?'Expense':'Manual journal entry')
  const [message,setMessage]=useState('')
  const debitAccounts=expense?accounts.filter(account=>account.account_type==='EXPENSE'):accounts
  const creditAccounts=expense?accounts.filter(account=>account.is_cash_account||account.account_type==='LIABILITY'):accounts
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setMessage('');try{await postJournalEntry({transaction_date:date,description,lines:[{account_code:Number(debitCode),debit:Number(amount),credit:0},{account_code:Number(creditCode),debit:0,credit:Number(amount)}]});setAmount('');setMessage(t(expense?'Expense posted successfully.':'Journal entry posted successfully.'))}catch(reason){setMessage(reason instanceof Error?reason.message:t('Unable to post journal entry.'))}}
  return <OperationForm title={t(expense?'Expense details':'Manual journal entry')} onSubmit={submit}>
    <div className="standard-operation__grid">
      <label><span>{t(expense?'Expense category':'Debit account')}</span><select value={debitCode} onChange={event=>setDebitCode(event.target.value)} disabled={loading}><option value="">{t('Select debit account')}</option>{debitAccounts.map(account=><option value={account.code} key={account.code}>{account.name}</option>)}</select></label>
      <label><span>{t(expense?'Payment account':'Credit account')}</span><select value={creditCode} onChange={event=>setCreditCode(event.target.value)} disabled={loading}><option value="">{t('Select credit account')}</option>{creditAccounts.filter(account=>String(account.code)!==debitCode).map(account=><option value={account.code} key={account.code}>{account.name}</option>)}</select></label>
      <label><span>{t('Amount')}</span><input type="number" min="0.01" step="0.01" value={amount} onChange={event=>setAmount(event.target.value)}/></label>
      <label><span>{t('Posting date')}</span><input type="datetime-local" value={date} onChange={event=>setDate(event.target.value)}/></label>
      <label><span>{t('Description')}</span><input value={description} onChange={event=>setDescription(event.target.value)}/></label>
    </div>
    <div className="income-operation__actions"><span>{message||error}</span><button type="submit" disabled={loading||!debitCode||!creditCode||!amount||!date}>{t(expense?'Post expense':'Post entry')}</button></div>
  </OperationForm>
}
