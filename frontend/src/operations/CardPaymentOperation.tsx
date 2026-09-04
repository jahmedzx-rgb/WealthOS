import { useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { recordCardPayment } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency } from '../context/CurrencyContext'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { useLanguage } from '../context/LanguageContext'

export default function CardPaymentOperation() {
  const imported=useImportedOperationDraft()
  const [searchParams]=useSearchParams()
  const {loading,error}=usePostingAccounts()
  const financial=useFinancialSummary()
  const {formatMoney}=useCurrency()
  const {t}=useLanguage()
  const [cardId,setCardId]=useState(searchParams.get('card')??'')
  const [bankId,setBankId]=useState('')
  const [amount,setAmount]=useState(imported.draft?.amount==null?'':String(Math.abs(imported.draft.amount)))
  const [date,setDate]=useState(toLocalDateTime(imported.draft?.transaction_date))
  const [description,setDescription]=useState(imported.draft?.description||t('Credit Card Payment'))
  const [message,setMessage]=useState('')
  const cards=financial.data?.credit_cards??[]
  const banks=financial.data?.bank_accounts??[]
  const matchedImportedCard=imported.draft?.card_last4?cards.find(card=>card.last4===imported.draft?.card_last4):undefined
  const effectiveCardId=cardId||String(matchedImportedCard?.id??'')
  const selectedCard=cards.find(card=>String(card.id)===effectiveCardId)
  const statementBalance=selectedCard?.statement_balance??0
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();setMessage('');try{const result=await recordCardPayment({credit_card_id:Number(effectiveCardId),bank_account_id:Number(bankId),credit_card_account_code:2110,payment_account_code:1120,amount:Number(amount),transaction_date:date,description});await imported.confirm(postingReference(result,'credit-card-payment'),'CREDIT_CARD',Number(effectiveCardId));setAmount('');setMessage(t('Credit Card Payment Posted Successfully.'))}catch(reason){setMessage(t(reason instanceof Error?reason.message:'Unable to post the card payment.'))}}
  return <OperationForm title="Credit Card Payment" onSubmit={submit}>
    <section className="card-payment__statement">
      <div><span>{t('Current Statement Balance')}</span><strong><FormattedMoney value={formatMoney(statementBalance)}/></strong></div>
      <p className="card-payment__tracking-note">{t('Enter the amount actually paid to the bank. WealthOS tracks the payment and remaining card balance.')}</p>
    </section>
    <div className="standard-operation__grid">
      <label><span>{t('Credit Card')}</span><select value={effectiveCardId} onChange={event=>{setCardId(event.target.value);if(!imported.draft)setAmount('')}} disabled={loading||financial.loading}><option value="">{t('Select Credit Card')}</option>{cards.map(card=><option value={card.id} key={card.id}>{card.card_name} •• {card.last4}</option>)}</select></label>
      <label><span>{t('Payment Account')}</span><select value={bankId} onChange={event=>setBankId(event.target.value)} disabled={loading||financial.loading}><option value="">{t('Select Bank Account')}</option>{banks.map(bank=><option value={bank.id} key={bank.id}>{bank.account_name} · {bank.bank_name}</option>)}</select></label>
      <label><span>{t('Amount Paid')}</span><input type="number" min="0.01" step="0.01" max={statementBalance||undefined} value={amount} onChange={event=>setAmount(event.target.value)}/></label>
      <label><span>{t('Payment Date')}</span><input type="datetime-local" value={date} onChange={event=>setDate(event.target.value)}/></label>
      <label><span>{t('Description')}</span><input value={description} onChange={event=>setDescription(event.target.value)}/></label>
    </div>
    <div className="income-operation__actions"><span>{message||(error?t(error):'')||(financial.error?t(financial.error):'')}</span><button type="submit" disabled={loading||financial.loading||!effectiveCardId||!bankId||Number(amount)<=0||!date}>{t('Post Payment')}</button></div>
  </OperationForm>
}
