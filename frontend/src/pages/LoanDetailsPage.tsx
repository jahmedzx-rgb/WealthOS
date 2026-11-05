import { CalendarDays, CheckCircle2, Landmark, ReceiptText } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'
import { useParams } from 'react-router-dom'
import FormattedMoney from '../components/ui/FormattedMoney'
import PageHeader from '../components/ui/PageHeader'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import { getLoans, getLoanPayments, getPrivateLoanHistory, type Loan, type LoanPayment, type PrivateLoanEvent } from '../services/accountingService'
import { displayLocale, formatDisplayInteger, formatDisplayPercent } from '../utils/localeFormat'
import { projectedEarlySettlement } from '../utils/loanProjection'
import './LoanDetailsPage.css'
import './LoanDetailsTypography.css'

function addMonths(dateValue:string, months:number, preferredDay?:number) {
  const [year,month,day]=dateValue.split('-').map(Number)
  const target=new Date(Date.UTC(year,month-1+months,1))
  const lastDay=new Date(Date.UTC(target.getUTCFullYear(),target.getUTCMonth()+1,0)).getUTCDate()
  target.setUTCDate(Math.min(preferredDay??day,lastDay))
  return target
}

export default function LoanDetailsPage(){
  const {loanId}=useParams()
  const [loan,setLoan]=useState<Loan|null>(null)
  const [history,setHistory]=useState<PrivateLoanEvent[]>([])
  const [payments,setPayments]=useState<LoanPayment[]>([])
  const [loading,setLoading]=useState(true)
  const {t,language}=useLanguage()
  const currency=useCurrency()
  const money=(value:number)=><FormattedMoney value={currency.formatMoney(value)}/>
  useEffect(()=>{getLoans().then(async items=>{const found=items.find(item=>String(item.id)===loanId)??null;setLoan(found);if(found?.loan_type==='PRIVATE_FLEXIBLE')setHistory(await getPrivateLoanHistory(found.id));else if(found)setPayments(await getLoanPayments(found.id))}).finally(()=>setLoading(false))},[loanId])
  const details=loan?.private_details
  const paymentDay=Number(details?.payment_day??loan?.first_payment_date?.slice(-2)??1)
  const remaining=loan ? Number(details?.remaining_installments ?? Math.ceil(Number(loan.outstanding_balance)/Number(loan.monthly_payment||1))) : 0
  const completed=loan ? Math.max(0,Number(loan.term_months)-remaining) : 0
  const totalRepayment=loan ? Number(loan.monthly_payment)*Number(loan.term_months) : 0
  const paidScheduled=loan ? Number(loan.monthly_payment)*completed : 0
  const earlySettlement=loan?projectedEarlySettlement(loan):null
  const schedule=useMemo(()=>{
    if(!loan?.first_payment_date||remaining<=0)return []
    let balance=Number(loan.outstanding_balance)
    const rate=Number(loan.annual_rate)/1200
    return Array.from({length:remaining},(_,index)=>{
      const installmentNumber=completed+index+1
      const interest=Math.round(balance*rate*100)/100
      const amount=Math.min(Number(loan.monthly_payment),balance+interest)
      balance=Math.max(0,balance-(amount-interest))
      return {installmentNumber,date:addMonths(loan.first_payment_date!,installmentNumber-1,paymentDay),amount}
    })
  },[loan,remaining,completed,paymentDay])
  const date=(value:Date|string)=>new Intl.DateTimeFormat(displayLocale(language),{day:'2-digit',month:'short',year:'numeric'}).format(typeof value==='string'?new Date(`${value}T12:00:00`):value)
  if(loading)return <section className="loan-details-page"><p>{t('Loading loan details…')}</p></section>
  if(!loan)return <section className="loan-details-page"><div className="loan-details-page__empty">{t('Loan not found.')}</div></section>
  if(loan.loan_type==='PRIVATE_FLEXIBLE'){
    const original=Number(details?.principal??loan.principal_amount)
    const agreedExtra=Number(details?.agreed_extra??0)
    const priorPaid=Number(details?.prior_paid??0)
    return <section className="loan-details-page">
      <PageHeader eyebrow={t('Private loan details')} title={loan.name} subtitle={`${loan.lender} · ${t('Private loan — flexible repayment')}`} icon={Landmark}/>
      <div className="loan-details-page__hero">
        <article><span>{t('Outstanding balance')}</span><strong>{money(Number(loan.outstanding_balance))}</strong><small>{t(loan.status==='SETTLED'?'Fully repaid':'Active private obligation')}</small></article>
        <article><span>{t('Original financing')}</span><strong>{money(original)}</strong><small>{t('Recorded principal')}</small></article>
        <article><span>{t('Paid before opening')}</span><strong>{money(priorPaid)}</strong><small>{t('Historical payments')}</small></article>
        <article><span>{t('Status')}</span><strong>{t(loan.status==='SETTLED'?'Settled':'Active')}</strong><small>{t('No fixed end date')}</small></article>
      </div>
      <div className="loan-details-page__layout">
        <section className="loan-details-card"><header><ReceiptText size={17}/><div><h2>{t('Loan agreement')}</h2><p>{t('Read-only financing details')}</p></div></header><dl>
          <div><dt>{t('Original financing')}</dt><dd>{money(original)}</dd></div><div><dt>{t('Agreed additional amount')}</dt><dd>{money(agreedExtra)}</dd></div><div><dt>{t('Total obligation')}</dt><dd>{money(original+agreedExtra)}</dd></div><div><dt>{t('Opening date')}</dt><dd>{details?.record_date?date(details.record_date):'—'}</dd></div><div><dt>{t('Current balance')}</dt><dd>{money(Number(loan.outstanding_balance))}</dd></div><div><dt>{t('Loan End Date')}</dt><dd>{t(loan.status==='SETTLED'?'Completed':'Open-ended')}</dd></div>
        </dl></section>
        <section className="loan-details-card loan-details-schedule"><header><CalendarDays size={17}/><div><h2>{t('Payment history')}</h2><p>{t('Recorded opening balance and repayments')}</p></div></header><div className="loan-details-schedule__head"><span>#</span><span>{t('Date')}</span><span>{t('Amount')}</span><span>{t('Status')}</span></div><div className="loan-details-schedule__rows">{history.map((item,index)=><div key={item.id}><span>{formatDisplayInteger(index+1,language)}</span><span>{date(item.event_date)}</span><strong>{money(Number(item.amount))}</strong><em><CheckCircle2 size={12}/>{t(item.kind==='PAYMENT'?'Paid':'Recorded')}</em></div>)}</div></section>
      </div>
    </section>
  }
  const endDate=loan.first_payment_date?addMonths(loan.first_payment_date,Number(loan.term_months)-1,paymentDay):null
  return <section className="loan-details-page">
    <PageHeader eyebrow={t('Loan details')} title={loan.name} subtitle={`${loan.lender} · ${t(loan.loan_type==='LONG_TERM'?'Long term':loan.loan_type==='SHORT_TERM'?'Short term':'Mortgage')}`} icon={Landmark}/>
    <div className="loan-details-page__hero">
      <article><span>{t('Current Outstanding Balance')}</span><strong>{money(Number(loan.outstanding_balance))}</strong><small>{t('Bank-aligned opening liability')}</small></article>
      <article><span>{t('Remaining Installments')}</span><strong>{formatDisplayInteger(remaining,language)}</strong><small>{money(Number(loan.monthly_payment))} / {t('month')}</small></article>
      <article><span>{t('Loan End Date')}</span><strong>{endDate?date(endDate):'—'}</strong><small>{t('Calculated from the original schedule')}</small></article>
      <article><span>{t('Repayment Progress')}</span><strong>{formatDisplayInteger(completed,language)} / {formatDisplayInteger(Number(loan.term_months),language)}</strong><small>{formatDisplayPercent(Number(loan.term_months)?completed/Number(loan.term_months)*100:0,1,language)}</small></article>
    </div>
    <div className="loan-details-page__layout">
      <section className="loan-details-card">
        <header><ReceiptText size={17}/><div><h2>{t('Financing details')}</h2><p>{t('Original agreement and current position')}</p></div></header>
        <dl>
          <div><dt>{t('Original Principal')}</dt><dd>{money(Number(loan.principal_amount))}</dd></div>
          <div><dt>{t('Net Amount Received')}</dt><dd>{money(Number(loan.amount_received))}</dd></div>
          <div><dt>{t('Upfront Fees')}</dt><dd>{money(Number(loan.fees))}</dd></div>
          <div><dt>{t('Annual Rate')}</dt><dd>{formatDisplayPercent(Number(loan.annual_rate),2,language)}</dd></div>
          <div><dt>{t('Original Term')}</dt><dd>{formatDisplayInteger(Number(loan.term_months),language)} {t('months')}</dd></div>
          <div><dt>{t('First Payment')}</dt><dd>{loan.first_payment_date?date(loan.first_payment_date):'—'}</dd></div>
          <div><dt>{t('Expected Total Repayment')}</dt><dd>{money(totalRepayment)}</dd></div>
          {earlySettlement?<div><dt>{t('Estimated Early Settlement')}</dt><dd>{money(earlySettlement.amount)}</dd></div>:null}
          <div><dt>{t('Scheduled payments completed')}</dt><dd>{money(paidScheduled)}</dd></div>
        </dl>
      </section>
      <section className="loan-details-card loan-details-schedule">
        <header><CalendarDays size={17}/><div><h2>{t('Repayment schedule')}</h2><p>{t('Upcoming installments through the loan end date')}</p></div></header>
        <div className="loan-details-schedule__head"><span>#</span><span>{t('Due Date')}</span><span>{t('Amount')}</span><span>{t('Status')}</span></div>
        <div className="loan-details-schedule__rows">{schedule.map((item,index)=><div key={item.installmentNumber}><span>{formatDisplayInteger(item.installmentNumber,language)}</span><span>{date(item.date)}</span><strong>{money(item.amount)}</strong><em className={index===0?'is-next':''}><CheckCircle2 size={12}/>{t(index===0?'Next':'Upcoming')}</em></div>)}</div>
      </section>
      <section className="loan-details-card loan-details-schedule"><header><ReceiptText size={17}/><div><h2>{t('Payment history')}</h2><p>{t('Recorded monthly installments and their principal and interest split.')}</p></div></header>{payments.length?<><div className="loan-details-schedule__head"><span>#</span><span>{t('Date')}</span><span>{t('Amount')}</span><span>{t('Balance after payment')}</span></div><div className="loan-details-schedule__rows">{payments.map(payment=><div key={payment.id}><span>{formatDisplayInteger(payment.installment_number,language)}</span><span>{date(payment.payment_date)}</span><strong>{money(Number(payment.amount))}<small>{t('Principal')}: {money(Number(payment.principal_paid))} · {t('Interest')}: {money(Number(payment.interest_paid))}</small></strong><em>{money(Number(payment.outstanding_after))}</em></div>)}</div></>:<p className="loan-details-schedule__empty">{t('No monthly payments recorded yet.')}</p>}</section>
    </div>
  </section>
}
