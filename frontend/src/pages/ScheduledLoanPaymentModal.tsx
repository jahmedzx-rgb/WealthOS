import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { HandCoins, X } from 'lucide-react'
import DateInput from '../components/DateInput'
import { recordLoanPayment, type BankAccount, type Loan, type LoanPayment } from '../services/accountingService'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import './ScheduledLoanPaymentModal.css'

function today(){const value=new Date();return `${value.getFullYear()}-${String(value.getMonth()+1).padStart(2,'0')}-${String(value.getDate()).padStart(2,'0')}`}
function estimatedInstallments(balance:number,payment:number,annualRate:number,term:number){if(balance<=0||payment<=0)return 0;const rate=annualRate/1200;if(!rate)return Math.min(term,Math.ceil(balance/payment));const ratio=rate*balance/payment;if(ratio>=1)return term;return Math.min(term,Math.ceil(-Math.log(1-ratio)/Math.log(1+rate)))}

export default function ScheduledLoanPaymentModal({loan,banks,onClose,onPaid}:{loan:Loan;banks:BankAccount[];onClose:()=>void;onPaid:(payment:LoanPayment)=>void}){
  const {t}=useLanguage(),{formatMoney}=useCurrency()
  const [amount,setAmount]=useState(()=>String(Math.min(Number(loan.monthly_payment),Number(loan.outstanding_balance)+Math.round(Number(loan.outstanding_balance)*Number(loan.annual_rate)/1200*100)/100))),[date,setDate]=useState(today()),[bank,setBank]=useState(String(loan.private_details?.payment_bank_account_id??loan.destination_bank_account_id??banks.find(item=>item.is_primary)?.id??banks[0]?.id??'')),[note,setNote]=useState(''),[error,setError]=useState(''),[saving,setSaving]=useState(false),[key]=useState(()=>crypto.randomUUID())
  const amountValue=Number(amount)||0,balance=Number(loan.outstanding_balance),interest=Math.round(balance*Number(loan.annual_rate)/1200*100)/100,principal=Math.max(0,amountValue-interest),remainingAfter=estimatedInstallments(Math.max(0,balance-principal),Number(loan.monthly_payment),Number(loan.annual_rate),loan.term_months)
  const availableBanks=useMemo(()=>banks.filter(item=>item.currency_code==='SAR'),[banks])
  useEffect(()=>{if(!bank&&availableBanks[0])setBank(String(availableBanks[0].id))},[bank,availableBanks])
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setSaving(true);setError('');try{const payment=await recordLoanPayment(loan.id,{amount:amountValue,payment_date:date,payment_bank_account_id:Number(bank),idempotency_key:key,note});onPaid(payment)}catch(reason){setError(t(reason instanceof Error?reason.message:'Unable to record this installment.'))}finally{setSaving(false)}}
  const valid=amountValue>interest&&principal<=balance&&Boolean(date&&bank&&availableBanks.some(item=>String(item.id)===bank))
  return <div className="scheduled-loan-payment" role="presentation" onMouseDown={event=>{if(event.target===event.currentTarget&&!saving)onClose()}}><form onSubmit={submit} role="dialog" aria-modal="true" aria-labelledby="scheduled-loan-payment-title">
    <header><div><small>{t('Monthly installment')}</small><h2 id="scheduled-loan-payment-title">{loan.name}</h2><p>{loan.lender}</p></div><button type="button" onClick={onClose} disabled={saving} aria-label={t('Close')}><X size={18}/></button></header>
    <div className="scheduled-loan-payment__fields"><label><span>{t('Installment amount')}</span><input autoFocus required type="number" min="0.01" step="0.01" value={amount} onChange={event=>setAmount(event.target.value)}/></label><label><span>{t('Payment date')}</span><DateInput required value={date} onChange={event=>setDate(event.target.value)}/></label><label className="is-wide"><span>{t('Payment bank account')}</span><select required value={bank} onChange={event=>setBank(event.target.value)}><option value="">{t('Select a bank account')}</option>{availableBanks.map(item=><option key={item.id} value={item.id}>{item.bank_name} · {item.account_name} · {item.account_identifier}</option>)}</select></label><label className="is-wide"><span>{t('Notes')} <em>{t('Optional')}</em></span><input maxLength={500} value={note} onChange={event=>setNote(event.target.value)}/></label></div>
    <section className="scheduled-loan-payment__preview"><div><span>{t('Estimated interest')}</span><strong>{formatMoney(interest,'SAR')}</strong></div><div><span>{t('Principal reduction')}</span><strong>{formatMoney(principal,'SAR')}</strong></div><div><span>{t('Balance after payment')}</span><strong>{formatMoney(Math.max(0,balance-principal),'SAR')}</strong></div><div><span>{t('Installments remaining')}</span><strong>{remainingAfter}</strong></div><small>{t('Interest is estimated using the annual rate divided monthly; verify it against the lender statement.')}</small></section>
    {error&&<p className="scheduled-loan-payment__error" role="alert">{error}</p>}
    <footer><span><HandCoins size={14}/>{t('Records the payment in the ledger and updates the loan and bank balances.')}</span><button type="button" onClick={onClose} disabled={saving}>{t('Cancel')}</button><button type="submit" disabled={!valid||saving}>{saving?t('Processing…'):t('Confirm payment')}</button></footer>
  </form></div>
}
