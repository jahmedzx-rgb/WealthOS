import { useEffect, useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import { createBankCard, getBankAccounts, type BankAccount } from '../services/accountingService'
import { useLanguage } from '../context/LanguageContext'

export default function BankCardOperation(){
  const{t}=useLanguage()
  const[banks,setBanks]=useState<BankAccount[]>([]);const[message,setMessage]=useState('');const[saving,setSaving]=useState(false)
  const[form,setForm]=useState({bank_account_id:'',card_name:'',last4:'',card_network:'MADA'})
  useEffect(()=>{void getBankAccounts().then(setBanks).catch(error=>setMessage(t(error instanceof Error?error.message:'Unable to load bank accounts.')))},[t])
  const bank=banks.find(item=>item.id===Number(form.bank_account_id))
  const set=(key:string,value:string)=>setForm(current=>({...current,[key]:value}))
  async function submit(event:FormEvent){event.preventDefault();setMessage('');setSaving(true);try{await createBankCard({...form,bank_account_id:Number(form.bank_account_id)});setMessage(t('Debit card linked successfully.'));setForm({bank_account_id:'',card_name:'',last4:'',card_network:'MADA'})}catch(error){setMessage(t(error instanceof Error?error.message:'Unable to link the debit card.'))}finally{setSaving(false)}}
  return <OperationForm title="Bank debit card details" onSubmit={event=>void submit(event)} preview={<div className="standard-operation__preview"><span>{t('Linked Account')}</span><strong>{bank?.account_name??t('Select an account')}</strong><small>{form.card_name||t('New Debit Card')}{form.last4?` · •• ${form.last4}`:''}</small></div>}>
    <div className="standard-operation__grid">
      <label><span>{t('Linked Bank Account')}</span><select required value={form.bank_account_id} onChange={event=>set('bank_account_id',event.target.value)}><option value="">{t('Select Bank Account')}</option>{banks.map(item=><option value={item.id} key={item.id}>{item.account_name} · {item.bank_name} · {item.currency_code}</option>)}</select></label>
      <label><span>{t('Card Name')}</span><input required maxLength={120} value={form.card_name} onChange={event=>set('card_name',event.target.value)} placeholder={t('e.g. Primary Mada Card')}/></label>
      <label><span>{t('Last 4 Digits')}</span><input required inputMode="numeric" pattern="\d{4}" maxLength={4} value={form.last4} onChange={event=>set('last4',event.target.value.replace(/\D/g,'').slice(0,4))} placeholder="0000"/></label>
      <label><span>{t('Card Network')}</span><select value={form.card_network} onChange={event=>set('card_network',event.target.value)}><option value="MADA">{t('Mada')}</option><option value="VISA">{t('Visa Debit')}</option><option value="MASTERCARD">{t('Mastercard Debit')}</option><option value="OTHER">{t('Other')}</option></select></label>
      <label><span>{t('Currency')}</span><input readOnly value={bank?.currency_code??t('From Linked Account')}/></label>
    </div>
    <div className="income-operation__actions"><span>{message||t('The card will inherit the linked account currency and balance.')}</span><button type="submit" disabled={saving||!bank}>{t(saving?'Linking…':'Link Debit Card')}</button></div>
  </OperationForm>
}
