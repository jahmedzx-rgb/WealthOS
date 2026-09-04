import { useState } from 'react'

import { updatePositionFairValue } from '../../services/portfolioService'
import { useCurrency, type Currency } from '../../context/CurrencyContext'
import FormattedMoney from '../ui/FormattedMoney'
import './FairValueEditor.css'

type Props = { portfolioId:number; securityId:number; value:number|null; currency:Currency; onSaved?:(value:number|null)=>void }

export default function FairValueEditor({portfolioId,securityId,value,currency,onSaved}:Props){
  const{formatMoney}=useCurrency();const[editing,setEditing]=useState(false);const[input,setInput]=useState(value?String(value):'');const[saving,setSaving]=useState(false);const[error,setError]=useState('')
  async function save(){const parsed=input.trim()?Number(input):null;if(parsed!==null&&(!Number.isFinite(parsed)||parsed<=0)){setError('Enter a valid value.');return}setSaving(true);setError('');try{await updatePositionFairValue(portfolioId,securityId,parsed);setEditing(false);onSaved?.(parsed)}catch(reason){setError(reason instanceof Error?reason.message:'Unable to save fair value.')}finally{setSaving(false)}}
  if(!editing)return <span className="fair-value-editor"><span>{value?<><small>Fair Value</small><FormattedMoney value={formatMoney(value,currency)}/></>:'Fair Value Not Set'}</span><button type="button" onClick={(event)=>{event.stopPropagation();setInput(value?String(value):'');setEditing(true)}}>{value?'Edit':'Add'}</button></span>
  return <span className="fair-value-editor is-editing" onClick={event=>event.stopPropagation()}><input autoFocus type="number" min="0.01" step="0.01" value={input} onChange={event=>setInput(event.target.value)} placeholder="Fair value"/><button type="button" disabled={saving} onClick={()=>void save()}>{saving?'Saving':'Save'}</button><button type="button" onClick={()=>{setEditing(false);setError('')}}>Cancel</button>{error?<small>{error}</small>:null}</span>
}
