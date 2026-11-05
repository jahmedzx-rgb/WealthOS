import DateInput from '../components/DateInput'
import { useEffect, useRef, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { recordCardPayment } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency } from '../context/CurrencyContext'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { useLanguage } from '../context/LanguageContext'
import { bankIdentityKey } from '../components/ui/BankIdentity'

const paymentBankLabel=(bank:{bank_name:string;account_identifier:string})=>{const last4=bank.account_identifier.replace(/\D/g,'').slice(-4);return `${bank.bank_name}${last4?` · ••••${last4}`:''}`}

export default function CardPaymentOperation() {
  const imported=useImportedOperationDraft()
  const [searchParams]=useSearchParams()
  const {loading,error}=usePostingAccounts()
  const financial=useFinancialSummary()
  const {formatMoney}=useCurrency()
  const {t,language}=useLanguage()
  const [cardId,setCardId]=useState(searchParams.get('card')??'')
  const [paymentSource,setPaymentSource]=useState<'BANK'|'CARD'>('BANK')
  const [bankId,setBankId]=useState('')
  const [sourceCardId,setSourceCardId]=useState('')
  const [amount,setAmount]=useState(imported.draft?.amount==null?'':String(Math.abs(imported.draft.amount)))
  const [date,setDate]=useState((toLocalDateTime(imported.draft?.transaction_date)||new Date().toLocaleDateString('en-CA')).slice(0,10))
  const [description,setDescription]=useState(imported.draft?.description||t('Credit Card Payment'))
  const [message,setMessage]=useState('')
  const [posting,setPosting]=useState(false)
  const postingRef=useRef(false)
  const cards=financial.data?.credit_cards??[]
  const banks=financial.data?.bank_accounts??[]
  const groupedBanks=[...banks].sort((a,b)=>bankIdentityKey(a.bank_name).localeCompare(bankIdentityKey(b.bank_name))||a.id-b.id)
  const matchedImportedCard=imported.draft?.card_last4?cards.find(card=>card.last4===imported.draft?.card_last4):undefined
  const effectiveCardId=cardId||String(matchedImportedCard?.id??'')
  const selectedCard=cards.find(card=>String(card.id)===effectiveCardId)
  const sourceCards=cards.filter(card=>String(card.id)!==effectiveCardId)
  const selectedSourceCard=cards.find(card=>String(card.id)===sourceCardId)
  const currentBalance=selectedCard?.current_balance??0
  useEffect(()=>{setAmount('');setMessage('')},[effectiveCardId])
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(postingRef.current)return;postingRef.current=true;setPosting(true);setMessage('');const now=new Date();const localTime=`${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;const transactionDate=new Date(`${date}T${localTime}`).toISOString();try{const result=await recordCardPayment({credit_card_id:Number(effectiveCardId),bank_account_id:paymentSource==='BANK'?Number(bankId):null,payment_credit_card_id:paymentSource==='CARD'?Number(sourceCardId):null,credit_card_account_code:2110,payment_account_code:paymentSource==='BANK'?1120:2110,amount:Number(amount),transaction_date:transactionDate,description});setAmount('');setMessage(t('Credit Card Payment Posted Successfully.'));await Promise.allSettled([imported.confirm(postingReference(result,'credit-card-payment'),'CREDIT_CARD',Number(effectiveCardId)),financial.refresh()])}catch(reason){setMessage(t(reason instanceof Error?reason.message:'Unable to post the card payment.'))}finally{postingRef.current=false;setPosting(false)}}
  return <OperationForm className="card-payment-operation" title="Credit Card Payment" onSubmit={submit}>
    <section className="card-payment__statement">
      <div><span>{t('Current Card Balance')}</span><strong><FormattedMoney value={formatMoney(currentBalance)}/></strong></div>
      <p className="card-payment__tracking-note">{t(paymentSource==='BANK'?'Enter the amount actually paid to the bank. WealthOS tracks the payment and remaining card balance.':'Pay the selected card through SADAD using another credit card. No bank cash flow is created.')}</p>
    </section>
    <div className="standard-operation__grid">
      <label><span>{t('Card Being Paid')}</span><select value={effectiveCardId} onChange={event=>{setCardId(event.target.value);if(event.target.value===sourceCardId)setSourceCardId('');if(!imported.draft)setAmount('')}} disabled={loading||financial.loading}><option value="">{t('Select Credit Card')}</option>{cards.map(card=><option value={card.id} key={card.id}>{card.issuer_bank} · {card.card_name} •• {card.last4}</option>)}</select></label>
      <label><span>{t('Payment Source')}</span><select value={paymentSource} onChange={event=>{setPaymentSource(event.target.value as 'BANK'|'CARD');setBankId('');setSourceCardId('')}}><option value="BANK">{t('Bank Account')}</option><option value="CARD">{t('Credit Card via SADAD')}</option></select></label>
      {paymentSource==='BANK'?<label><span>{t('Payment Account')}</span><select value={bankId} onChange={event=>setBankId(event.target.value)} disabled={loading||financial.loading}><option value="">{t('Select Bank Account')}</option>{groupedBanks.map(bank=><option value={bank.id} key={bank.id}>{paymentBankLabel(bank)}</option>)}</select></label>:<label><span>{t('Card Used for Payment')}</span><select value={sourceCardId} onChange={event=>setSourceCardId(event.target.value)} disabled={loading||financial.loading||!effectiveCardId}><option value="">{t('Select Payment Card')}</option>{sourceCards.map(card=><option value={card.id} key={card.id}>{card.issuer_bank} · {card.card_name} •• {card.last4}</option>)}</select></label>}
      <label><span>{t('Amount Paid')}</span><input type="number" min="0.01" step="0.01" value={amount} onChange={event=>setAmount(event.target.value)}/></label>
      <label><span>{t('Payment Date')}</span><DateInput type="date" value={date} onChange={event=>setDate(event.target.value)}/></label>
      <label><span>{t('Description')}</span><input value={description} onChange={event=>setDescription(event.target.value)}/></label>
    </div>
    {paymentSource==='CARD'&&selectedCard&&selectedSourceCard?<div className="card-payment__direction"><strong>{t('Payment Direction')}</strong><span>{language==='ar'?`سيتم سداد ${selectedCard.issuer_bank} · ${selectedCard.card_name} •• ${selectedCard.last4} باستخدام ${selectedSourceCard.issuer_bank} · ${selectedSourceCard.card_name} •• ${selectedSourceCard.last4}.`:`${selectedCard.issuer_bank} · ${selectedCard.card_name} •• ${selectedCard.last4} will be paid using ${selectedSourceCard.issuer_bank} · ${selectedSourceCard.card_name} •• ${selectedSourceCard.last4}.`}</span></div>:null}
    <div className="income-operation__actions"><span className={message===t('Credit Card Payment Posted Successfully.')?'is-success':undefined}>{message||(error?t(error):'')||(financial.error?t(financial.error):'')}</span><button type="submit" disabled={posting||loading||financial.loading||!effectiveCardId||(paymentSource==='BANK'?!bankId:!sourceCardId)||Number(amount)<=0||!date}>{t(posting?'Posting…':'Post Payment')}</button></div>
  </OperationForm>
}
