import { useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import { recordOtherAssetPurchase } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'

const types=[
  {value:'VEHICLE',label:'Vehicle',code:1220},
  {value:'GOLD',label:'Gold & Precious Metals',code:1150},
  {value:'EQUIPMENT',label:'Equipment',code:1230},
  {value:'COLLECTIBLE',label:'Art & Collectibles',code:1150},
  {value:'OTHER',label:'Other Asset',code:1150},
] as const
const amountInput=(value:string)=>{const cleaned=value.replace(/[^\d.]/g,'');const[whole='',...decimal]=cleaned.split('.');const grouped=whole.replace(/\B(?=(\d{3})+(?!\d))/g,',');return cleaned.includes('.')?`${grouped}.${decimal.join('').slice(0,2)}`:grouped}
const amountValue=(value:string)=>value.replace(/,/g,'').replace(/[^\d.]/g,'')

export default function BuyOtherAssetOperation(){
  const{t}=useLanguage()
  const financial=useFinancialSummary();const{formatMoney}=useCurrency();const[type,setType]=useState('');const[name,setName]=useState('');const[paymentSource,setPaymentSource]=useState<'BANK_ACCOUNT'|'CASH_ON_HAND'>('BANK_ACCOUNT');const[bankAccountId,setBankAccountId]=useState('');const[amount,setAmount]=useState('');const[date,setDate]=useState('');const[notes,setNotes]=useState('');const[message,setMessage]=useState('')
  const bankAccounts=financial.data?.bank_accounts??[];const selectedBank=bankAccounts.find(item=>item.id===Number(bankAccountId));const cashOnHand=financial.data?.asset_breakdown.find(item=>item.code===1110)?.balance??0;const available=paymentSource==='BANK_ACCOUNT'?(selectedBank?.current_balance??0):cashOnHand;const currency=paymentSource==='BANK_ACCOUNT'?(selectedBank?.currency_code??'SAR'):'SAR';const insufficient=Number(amount)>available;const selectedType=types.find(item=>item.value===type)
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(!selectedType||insufficient)return;setMessage('');try{await recordOtherAssetPurchase({asset_account_code:selectedType.code,payment_source:paymentSource,bank_account_id:paymentSource==='BANK_ACCOUNT'?Number(bankAccountId):null,amount:Number(amount),transaction_date:date,description:`${selectedType.label} Purchase: ${name}${notes.trim()?` · ${notes.trim()}`:''}`});setName('');setAmount('');setNotes('');await financial.refresh();setMessage(t('Other Asset Purchase Posted Successfully.'))}catch(reason){setMessage(t(reason instanceof Error?reason.message:'Unable to post the asset purchase.'))}}
  return <OperationForm title="Buy Other Asset" onSubmit={submit}><div className="standard-operation__grid">
    <label><span>{t('Asset Type')}</span><select value={type} onChange={event=>setType(event.target.value)}><option value="">{t('Select Asset Type')}</option>{types.map(item=><option value={item.value} key={item.value}>{t(item.label)}</option>)}</select></label>
    <label><span>{t('Asset Name')}</span><input value={name} onChange={event=>setName(event.target.value)} placeholder={t('e.g. Toyota Land Cruiser, Gold Bar')}/></label>
    <label><span>{t('Payment Source')}</span><select value={paymentSource} onChange={event=>setPaymentSource(event.target.value as typeof paymentSource)}><option value="BANK_ACCOUNT">{t('Bank Account')}</option><option value="CASH_ON_HAND">{t('Cash On Hand')}</option></select></label>
    {paymentSource==='BANK_ACCOUNT'?<label><span>{t('Bank Account')}</span><select value={bankAccountId} onChange={event=>setBankAccountId(event.target.value)}><option value="">{t('Select Bank Account')}</option>{bankAccounts.map(item=><option value={item.id} key={item.id}>{item.account_name} · {item.bank_name} · {formatMoney(item.current_balance,item.currency_code as Currency)}</option>)}</select></label>:<label><span>{t('Available Cash On Hand')}</span><input readOnly value={formatMoney(cashOnHand,'SAR')}/></label>}
    <label><span>{t('Purchase Amount')}</span><input inputMode="decimal" value={amountInput(amount)} onChange={event=>setAmount(amountValue(event.target.value))} placeholder="0.00"/></label>
    <label><span>{t('Purchase Date')}</span><input type="datetime-local" value={date} onChange={event=>setDate(event.target.value)}/></label>
    <label><span>{t('Notes')}</span><input value={notes} maxLength={120} onChange={event=>setNotes(event.target.value)} placeholder={t('Optional details or reference')}/></label>
  </div><div className="income-operation__actions"><span>{amount&&insufficient?`${t('Purchase amount exceeds the available balance of')} ${formatMoney(available,currency as Currency)}.`:message||(financial.error?t(financial.error):'')}</span><button type="submit" disabled={financial.loading||!type||!name.trim()||(paymentSource==='BANK_ACCOUNT'&&!bankAccountId)||!amount||!date||insufficient}>{t('Post Purchase')}</button></div></OperationForm>
}
