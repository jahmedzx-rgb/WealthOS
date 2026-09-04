import { useEffect, useState, type FormEvent } from 'react'
import OperationForm from './OperationForm'
import { adjustPropertyValue, getProperties, type PropertyAsset } from '../services/accountingService'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'

const localNow=()=>new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)
export default function PropertyValuationOperation(){
  const{t}=useLanguage()
  const{formatMoney}=useCurrency();const[properties,setProperties]=useState<PropertyAsset[]>([]);const[saving,setSaving]=useState(false);const[message,setMessage]=useState('')
  const[form,setForm]=useState({property_id:'',corrected_value:'',adjustment_date:localNow(),reason:''})
  useEffect(()=>{void getProperties().then(setProperties).catch(error=>setMessage(t(error instanceof Error?error.message:'Unable to load properties.')))},[t])
  const property=properties.find(item=>item.id===Number(form.property_id));const value=Number(form.corrected_value)||0
  const set=(key:string,value:string)=>setForm(current=>({...current,[key]:value}))
  async function submit(event:FormEvent){event.preventDefault();if(!property)return;setSaving(true);setMessage('');try{await adjustPropertyValue(property.id,{corrected_value:value,adjustment_date:new Date(form.adjustment_date).toISOString(),reason:form.reason});setMessage(t('Property valuation updated and posted to the ledger.'));setProperties(current=>current.map(item=>item.id===property.id?{...item,current_value:value}:item))}catch(error){setMessage(t(error instanceof Error?error.message:'Unable to update the valuation.'))}finally{setSaving(false)}}
  return <OperationForm title={t('Property valuation')} onSubmit={event=>void submit(event)} preview={<><div className="standard-operation__preview"><span>{t('Updated Value')}</span><strong>{formatMoney(value)}</strong><small>{property?.name??t('Select a property')}</small></div><div className="income-operation__effects"><h4>{t('Valuation Impact')}</h4><p><span>{t('Current Value')}</span><strong>{formatMoney(property?.current_value??0)}</strong></p><p><span>{t('Difference')}</span><strong>{formatMoney(value-(property?.current_value??0))}</strong></p><p><span>{t('Ledger')}</span><strong>{t('Balanced Revaluation Entry')}</strong></p></div></>}>
    <div className="standard-operation__grid">
      <label><span>{t('Property')}</span><select required value={form.property_id} onChange={event=>set('property_id',event.target.value)}><option value="">{t('Select Property')}</option>{properties.map(item=><option value={item.id} key={item.id}>{item.name} · {formatMoney(item.current_value)}</option>)}</select></label>
      <label><span>{t('Market Value')}</span><input required min="0" step="0.01" type="number" value={form.corrected_value} onChange={event=>set('corrected_value',event.target.value)} placeholder="0.00"/></label>
      <label><span>{t('Valuation Date')}</span><input required type="datetime-local" value={form.adjustment_date} onChange={event=>set('adjustment_date',event.target.value)}/></label>
      <label><span>{t('Valuation Source / Notes')}</span><input required minLength={3} maxLength={255} value={form.reason} onChange={event=>set('reason',event.target.value)} placeholder={t('e.g. Certified valuation or market estimate')}/></label>
    </div>
    <div className="income-operation__actions"><span>{message||t('Changes update the property value, wealth, and balance sheet together.')}</span><button type="submit" disabled={saving||!property||value<0}>{t(saving?'Posting…':'Update Valuation')}</button></div>
  </OperationForm>
}
