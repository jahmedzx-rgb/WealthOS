import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { adjustPropertyValue, getProperties, recordPropertyPurchase, updateProperty, type PropertyAsset, type PropertyIncomeType } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayNumber } from '../utils/localeFormat'

const amountInput=(value:string)=>{const cleaned=value.replace(/[^\d.]/g,'');const[whole='',...decimal]=cleaned.split('.');const grouped=whole.replace(/\B(?=(\d{3})+(?!\d))/g,',');return cleaned.includes('.')?`${grouped}.${decimal.join('').slice(0,2)}`:grouped}
const amountValue=(value:string)=>value.replace(/,/g,'').replace(/[^\d.]/g,'')

export default function PropertyPurchaseOperation() {
  const imported=useImportedOperationDraft()
  const [searchParams]=useSearchParams();const editId=searchParams.get('edit');const editMode=Boolean(editId)
  const {accounts,loading,error}=usePostingAccounts()
  const financial=useFinancialSummary()
  const {formatMoney}=useCurrency()
  const {t,language}=useLanguage()
  const [paymentSource,setPaymentSource]=useState<'BANK_ACCOUNT'|'CASH_ON_HAND'>('BANK_ACCOUNT')
  const [bankAccountId,setBankAccountId]=useState('')
  const [amount,setAmount]=useState(imported.draft?.amount==null?'':String(Math.abs(imported.draft.amount)))
  const [transferTax,setTransferTax]=useState('')
  const [date,setDate]=useState(toLocalDateTime(imported.draft?.transaction_date))
  const [name,setName]=useState(imported.draft?.description??'')
  const [propertyUsage,setPropertyUsage]=useState<''|'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER'>('')
  const [propertyIncomeType,setPropertyIncomeType]=useState<''|PropertyIncomeType>('')
  const [message,setMessage]=useState('')
  const [property,setProperty]=useState<PropertyAsset|null>(null)
  const [adjusting,setAdjusting]=useState(false)
  const [correctedValue,setCorrectedValue]=useState('')
  const [adjustmentDate,setAdjustmentDate]=useState('')
  const [adjustmentReason,setAdjustmentReason]=useState('')
  const propertyAccount=accounts.find(account=>account.name==='Real Estate')
  const bankAccounts=financial.data?.bank_accounts??[]
  const selectedBank=bankAccounts.find(account=>account.id===Number(bankAccountId))
  const cashOnHandBalance=financial.data?.asset_breakdown.find(item=>item.code===1110)?.balance??0
  const availableBalance=paymentSource==='BANK_ACCOUNT'?(selectedBank?.current_balance??0):cashOnHandBalance
  const availableCurrency=paymentSource==='BANK_ACCOUNT'?(selectedBank?.currency_code??'SAR'):'SAR'
  const totalCost=Number(amount)+Number(transferTax||0)
  const insufficient=totalCost>availableBalance
  useEffect(()=>{if(!editMode||!editId)return;getProperties().then(items=>{const item=items.find(value=>String(value.id)===editId);if(!item){setMessage(t('Property was not found.'));return}setProperty(item);setName(item.name);setPropertyUsage(item.usage==='UNSPECIFIED'?'':item.usage);setPropertyIncomeType(item.income_type??'');setCorrectedValue(String(item.current_value))}).catch(()=>setMessage(t('Unable to load the property.')))},[editId,editMode,t])
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(!propertyAccount||!propertyUsage||(propertyUsage==='INVESTMENT_PROPERTY'&&!propertyIncomeType)||(!editMode&&insufficient))return;setMessage('');try{if(editMode&&editId){await updateProperty(Number(editId),{property_name:name.trim(),property_usage:propertyUsage,property_income_type:propertyUsage==='INVESTMENT_PROPERTY'?propertyIncomeType as PropertyIncomeType:null});setMessage(t('Property details updated successfully.'))}else{const posted=await recordPropertyPurchase({property_account_code:propertyAccount.code,property_name:name,property_usage:propertyUsage,property_income_type:propertyUsage==='INVESTMENT_PROPERTY'?propertyIncomeType as PropertyIncomeType:null,payment_source:paymentSource,bank_account_id:paymentSource==='BANK_ACCOUNT'?Number(bankAccountId):null,amount:Number(amount),transfer_tax:Number(transferTax||0),transaction_date:date,description:`${t('Property purchase')}: ${name}${Number(transferTax)>0?` · ${t('Real Estate Transaction Tax')} ${formatDisplayNumber(Number(transferTax),undefined,language)}`:''}`});await imported.confirm(postingReference(posted,'property'),'PROPERTY');setAmount('');setTransferTax('');setName('');setPropertyUsage('');setPropertyIncomeType('');setMessage(t('Property purchase posted successfully.'))}await financial.refresh()}catch{setMessage(t('Unable to save the property.'))}}
  async function saveAdjustment(){if(!editId||!adjustmentDate||adjustmentReason.trim().length<3)return setMessage(t('Enter the corrected value, adjustment date, and a brief reason.'));try{const updated=await adjustPropertyValue(Number(editId),{corrected_value:Number(correctedValue),adjustment_date:new Date(adjustmentDate).toISOString(),reason:adjustmentReason.trim()});setProperty(current=>current?{...current,current_value:updated.current_value}:current);setCorrectedValue(String(updated.current_value));setAdjusting(false);setAdjustmentReason('');setMessage(t('Property value adjusted and accounting correction posted.'));await financial.refresh()}catch{setMessage(t('Unable to adjust the property value.'))}}
  return <OperationForm title={t(editMode?'Edit Property':'Buy Property')} onSubmit={submit}>
    <div className="standard-operation__grid">
      <label><span>{t('Property Name')}</span><input value={name} onChange={event=>setName(event.target.value)} placeholder={t('Property name or reference')}/></label>
      <label><span>{t('Property Usage')}</span><select required value={propertyUsage} onChange={event=>{const usage=event.target.value as typeof propertyUsage;setPropertyUsage(usage);if(usage!=='INVESTMENT_PROPERTY')setPropertyIncomeType('')}}><option value="" disabled>{t('Select Property Usage')}</option><option value="PRIMARY_RESIDENCE">{t('Primary Residence')}</option><option value="INVESTMENT_PROPERTY">{t('Investment Property')}</option><option value="VACATION_HOME">{t('Vacation Home')}</option><option value="OTHER">{t('Other')}</option></select></label>
      {propertyUsage==='INVESTMENT_PROPERTY'&&<label><span>{t('Property Income Type')}</span><select required autoFocus value={propertyIncomeType} onChange={event=>setPropertyIncomeType(event.target.value as PropertyIncomeType)}><option value="" disabled>{t('Select Income Type')}</option><option value="RESIDENTIAL_RENT">{t('Residential Rent')}</option><option value="COMMERCIAL_RENT">{t('Commercial Rent')}</option><option value="SHORT_TERM_RENT">{t('Short-term Rent')}</option></select></label>}
      {editMode?<><label><span>{t('Current Property Value')}</span><input readOnly value={formatMoney(property?.current_value??0,'SAR')}/></label><label><span>{t('Purchase Date')}</span><input readOnly value={property?.purchase_date??''}/></label></>:<>
      <label><span>{t('Payment Source')}</span><select value={paymentSource} onChange={event=>setPaymentSource(event.target.value as typeof paymentSource)}><option value="BANK_ACCOUNT">{t('Bank Account')}</option><option value="CASH_ON_HAND">{t('Cash On Hand')}</option></select></label>
      {paymentSource==='BANK_ACCOUNT'?<label><span>{t('Bank Account')}</span><select value={bankAccountId} onChange={event=>setBankAccountId(event.target.value)} disabled={financial.loading}><option value="">{t('Select Bank Account')}</option>{bankAccounts.map(account=><option value={account.id} key={account.id}>{account.account_name} · {account.bank_name} · {formatMoney(account.current_balance,account.currency_code as Currency)}</option>)}</select></label>:<label><span>{t('Available Cash On Hand')}</span><input readOnly value={formatMoney(cashOnHandBalance,'SAR')}/></label>}
      <label><span>{t('Purchase Amount')}</span><input type="text" inputMode="decimal" value={amountInput(amount)} onChange={event=>setAmount(amountValue(event.target.value))} placeholder="0.00"/></label>
      <label><span>{t('Real Estate Transaction Tax')} <small>{t('Optional')}</small></span><input type="text" inputMode="decimal" value={amountInput(transferTax)} onChange={event=>setTransferTax(amountValue(event.target.value))} placeholder={t('Leave blank if not applicable')}/></label>
      <label><span>{t('Purchase Date')}</span><input type="datetime-local" value={date} onChange={event=>setDate(event.target.value)}/></label>
      </>}
    </div>
    {editMode&&<div className="property-operation__adjust"><button className="credit-card-operation__adjust" type="button" onClick={()=>setAdjusting(value=>!value)}>{t('Adjust Property Value')}</button>{adjusting&&<div><label><span>{t('Corrected Value')}</span><input type="text" inputMode="decimal" value={amountInput(correctedValue)} onChange={event=>setCorrectedValue(amountValue(event.target.value))}/></label><label><span>{t('Adjustment Date')}</span><input type="datetime-local" value={adjustmentDate} onChange={event=>setAdjustmentDate(event.target.value)}/></label><label><span>{t('Reason')}</span><input value={adjustmentReason} onChange={event=>setAdjustmentReason(event.target.value)} placeholder={t('Why is this correction needed?')}/></label><button type="button" onClick={()=>void saveAdjustment()}>{t('Post Adjustment')}</button></div>}</div>}
    <div className="income-operation__actions"><span>{!editMode&&amount&&insufficient?`${t('Total purchase')} ${formatMoney(totalCost,availableCurrency as Currency)} ${t('exceeds the available balance')} ${formatMoney(availableBalance,availableCurrency as Currency)}.`:message||(error?t('Unable to load posting accounts.'):financial.error?t('Unable to load financial data.'):(editMode?t('Value changes remain protected and are recorded through posted accounting corrections.') :''))}</span><button type="submit" disabled={loading||financial.loading||!propertyAccount||!name.trim()||!propertyUsage||(propertyUsage==='INVESTMENT_PROPERTY'&&!propertyIncomeType)||(!editMode&&((paymentSource==='BANK_ACCOUNT'&&!bankAccountId)||!amount||!date||insufficient))}>{t(editMode?'Save Changes':'Post Purchase')}</button></div>
  </OperationForm>
}
