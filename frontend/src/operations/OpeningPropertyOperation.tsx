import DateInput from '../components/DateInput'
import { useRef, useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import { recordOpeningProperty, type PropertyIncomeType } from '../services/accountingService'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useLanguage } from '../context/LanguageContext'
import { useCurrency } from '../context/CurrencyContext'

import './OpeningPropertyOperation.css'

type Usage = ''|'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER'
const amountInput=(value:string)=>{const cleaned=value.replace(/[^\d.]/g,'');const[whole='',...decimal]=cleaned.split('.');const grouped=whole.replace(/\B(?=(\d{3})+(?!\d))/g,',');return cleaned.includes('.')?`${grouped}.${decimal.join('').slice(0,2)}`:grouped}
const amountValue=(value:string)=>value.replace(/[٠-٩۰-۹]/g,c=>String(c.charCodeAt(0)-(c>='۰'?1776:1632))).replace(/٫/g,'.').replace(/[,٬]/g,'').replace(/[^\d.]/g,'')
const isoDate=(value:string)=>value?`${value}T12:00:00`:null
const newKey=()=>`opening-property:${crypto.randomUUID()}`

export default function OpeningPropertyOperation(){
  const{t}=useLanguage();const financial=useFinancialSummary()
  const{formatMoney}=useCurrency()
  const[name,setName]=useState('');const[usage,setUsage]=useState<Usage>('');const[incomeType,setIncomeType]=useState<''|PropertyIncomeType>('')
  const[openingDate,setOpeningDate]=useState('');const[acquisitionDate,setAcquisitionDate]=useState('');const[purchasePrice,setPurchasePrice]=useState('');const[improvementCost,setImprovementCost]=useState('')
  const[purchaseEstimated,setPurchaseEstimated]=useState(false);const[improvementEstimated,setImprovementEstimated]=useState(false)
  const[includeMarket,setIncludeMarket]=useState(false);const[marketValue,setMarketValue]=useState('');const[marketSource,setMarketSource]=useState('');const[marketNote,setMarketNote]=useState('');const[externalReference,setExternalReference]=useState('')
  const[idempotencyKey]=useState(newKey);const[recorded,setRecorded]=useState(false);const submissionLock=useRef(false);const[message,setMessage]=useState('');const[submitting,setSubmitting]=useState(false)
  const invalidDate=Boolean(acquisitionDate&&openingDate&&acquisitionDate>openingDate)
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(!usage||invalidDate||submissionLock.current||recorded)return;submissionLock.current=true;setSubmitting(true);setMessage('');try{const result=await recordOpeningProperty({property_name:name.trim(),property_usage:usage,property_income_type:usage==='INVESTMENT_PROPERTY'?incomeType as PropertyIncomeType:null,opening_date:isoDate(openingDate)!,acquisition_date:isoDate(acquisitionDate),purchase_price:Number(purchasePrice||0),improvement_cost:Number(improvementCost||0),purchase_price_estimated:purchaseEstimated,improvement_cost_estimated:improvementEstimated,market_value:includeMarket?Number(marketValue):null,market_value_date:includeMarket?isoDate(openingDate):null,market_value_source:includeMarket?marketSource.trim():null,market_value_note:includeMarket?(marketNote.trim()||null):null,external_property_reference:externalReference.trim()||null,idempotency_key:idempotencyKey});setMessage(t(result.duplicate_warning?'Property recorded. A similar property already exists; review both records.':'Previously owned property recorded successfully.'));setRecorded(true);try{await financial.refresh()}catch{/* The write succeeded; a failed summary refresh must not enable another write. */}}catch(reason){setMessage(t(reason instanceof Error?reason.message:'Unable to record the previously owned property.'))}finally{submissionLock.current=false;setSubmitting(false)}}
  const preview=<>
    <div className="standard-operation__preview"><span>{t('Opening property cost')}</span><strong>{formatMoney(Number(purchasePrice||0)+Number(improvementCost||0),'SAR')}</strong><small>{name||t('Previously Owned Property')}</small></div>
    <div className="income-operation__effects">
      <h4>{t('Transaction preview')}</h4>
      <p><span>{t('Purchase Price')}{purchaseEstimated?` (${t('Estimated amount')})`:''}</span><strong>{formatMoney(Number(purchasePrice||0),'SAR')}</strong></p>
      <p><span>{t('Improvement Cost')}{improvementEstimated?` (${t('Estimated amount')})`:''}</span><strong>{formatMoney(Number(improvementCost||0),'SAR')}</strong></p>
      {includeMarket&&<p><span>{t('Opening Market Value')}</span><strong>{formatMoney(Number(marketValue||0),'SAR')}</strong></p>}
    </div>
    <div className="income-operation__smart-note"><p>{t(recorded?'Property Recorded':'Preview only — nothing has been saved.')}</p></div>
  </>
  return <OperationForm className="opening-property" title={t('Previously Owned Property')} onSubmit={submit} preview={preview}>
    <fieldset className="opening-property__fields" disabled={recorded}><div className="standard-operation__grid">
      <label><span>{t('Property Name')}</span><input required maxLength={160} value={name} onChange={event=>setName(event.target.value)} /></label>
      <label><span>{t('Property Usage')}</span><select required value={usage} onChange={event=>{const next=event.target.value as Usage;setUsage(next);if(next!=='INVESTMENT_PROPERTY')setIncomeType('')}}><option value="" disabled>{t('Select Property Usage')}</option><option value="PRIMARY_RESIDENCE">{t('Primary Residence')}</option><option value="INVESTMENT_PROPERTY">{t('Investment Property')}</option><option value="VACATION_HOME">{t('Vacation Home')}</option><option value="OTHER">{t('Other')}</option></select></label>
      {usage==='INVESTMENT_PROPERTY'&&<label><span>{t('Property Income Type')}</span><select required value={incomeType} onChange={event=>setIncomeType(event.target.value as PropertyIncomeType)}><option value="" disabled>{t('Select Income Type')}</option><option value="RESIDENTIAL_RENT">{t('Residential Rent')}</option><option value="COMMERCIAL_RENT">{t('Commercial Rent')}</option><option value="SHORT_TERM_RENT">{t('Short-term Rent')}</option></select></label>}
      <label><span>{t('Opening Balance Date')}</span><DateInput required type="date" value={openingDate} onChange={event=>setOpeningDate(event.target.value)} /></label>
      <label><span>{t('Acquisition Date')} <small>{t('Optional')}</small></span><DateInput type="date" max={openingDate||undefined} value={acquisitionDate} onChange={event=>setAcquisitionDate(event.target.value)} /></label>
      <div className="opening-property__cost"><label htmlFor="opening-purchase-price">{t('Purchase Price')}</label><input id="opening-purchase-price" required inputMode="decimal" value={amountInput(purchasePrice)} onChange={event=>setPurchasePrice(amountValue(event.target.value))} placeholder="0.00"/><label className="opening-property__check"><input type="checkbox" checked={purchaseEstimated} onChange={event=>setPurchaseEstimated(event.target.checked)}/><span>{t('Estimated amount')}</span></label></div>
      <div className="opening-property__cost"><label htmlFor="opening-improvement-cost">{t('Improvement Cost')}</label><input id="opening-improvement-cost" inputMode="decimal" value={amountInput(improvementCost)} onChange={event=>setImprovementCost(amountValue(event.target.value))} placeholder="0.00"/><label className="opening-property__check"><input type="checkbox" checked={improvementEstimated} onChange={event=>setImprovementEstimated(event.target.checked)}/><span>{t('Estimated amount')}</span></label></div>
      <label><span>{t('External Property Reference')} <small>{t('Optional')}</small></span><input maxLength={120} value={externalReference} onChange={event=>setExternalReference(event.target.value)}/></label>
    </div>
    <label className="opening-property__check"><input type="checkbox" checked={includeMarket} onChange={event=>setIncludeMarket(event.target.checked)}/><span>{t('Add an opening market value')}</span></label>
    {includeMarket&&<div className="standard-operation__grid"><label><span>{t('Opening Market Value')}</span><input required inputMode="decimal" value={amountInput(marketValue)} onChange={event=>setMarketValue(amountValue(event.target.value))} placeholder="0.00"/></label><label><span>{t('Valuation Date')}</span><DateInput type="date" readOnly value={openingDate}/></label><label><span>{t('Valuation Source')}</span><input required maxLength={160} value={marketSource} onChange={event=>setMarketSource(event.target.value)}/></label><label><span>{t('Valuation Note')} <small>{t('Optional')}</small></span><input maxLength={500} value={marketNote} onChange={event=>setMarketNote(event.target.value)}/></label></div>}
    </fieldset>
    <div className="income-operation__smart-note"><p><strong>{t('Opening asset — not a purchase or income')}</strong>{t('This records property already owned before WealthOS. It does not reduce bank or cash balances and does not record revenue or expense. Opening cost-basis corrections are not available yet; later market values use the property valuation operation.')}</p></div>
    <div className="income-operation__actions"><span>{invalidDate?t('Acquisition date cannot be after the opening date.'):message}</span><button type="submit" disabled={recorded||submitting||!name.trim()||!usage||(usage==='INVESTMENT_PROPERTY'&&!incomeType)||!openingDate||(!Number(purchasePrice)&&!Number(improvementCost))||invalidDate||(includeMarket&&(!Number(marketValue)||!marketSource.trim()))}>{t(recorded?'Property Recorded':submitting?'Recording Property…':'Record Opening Property')}</button></div>
  </OperationForm>
}
