import { useState } from 'react'
import { Plus, Trash2, X } from 'lucide-react'
import { addPrivateLoanPriorPayments, type Loan, type PrivateLoanEvent } from '../services/accountingService'
import { displayAmountInput, parseAmountInput } from '../utils/amountInput'
import { useLanguage } from '../context/LanguageContext'

type Row={id:string;year:string;amount:string;source:string;note:string}
const newRow=():Row=>({id:crypto.randomUUID(),year:'',amount:'',source:'',note:''})
const dateWithinPreOpeningYear=(year:string,openingDate:string)=>{
  if(!openingDate.startsWith(`${year}-`)) return `${year}-12-31`
  const dayBeforeOpening=new Date(`${openingDate}T00:00:00Z`)
  dayBeforeOpening.setUTCDate(dayBeforeOpening.getUTCDate()-1)
  return dayBeforeOpening.toISOString().slice(0,10)
}

export default function PriorPaymentDetails({loan,history,onAdded}:{loan:Loan;history:PrivateLoanEvent[];onAdded:(items:PrivateLoanEvent[])=>void}) {
  const {t,language}=useLanguage(),[open,setOpen]=useState(false),[rows,setRows]=useState<Row[]>([newRow()]),[saving,setSaving]=useState(false),[error,setError]=useState('')
  const recorded=history.filter(item=>item.kind==='PRIOR_PAYMENT_DETAIL').reduce((sum,item)=>sum+Number(item.amount),0)
  const target=Number(loan.private_details?.prior_paid??0),remaining=target-recorded,total=rows.reduce((sum,row)=>sum+Number(row.amount||0),0)
  const valid=rows.every(row=>row.year&&row.source.trim()&&Number(row.amount)>0)&&total<=remaining
  const update=(id:string,key:keyof Omit<Row,'id'>,value:string)=>setRows(current=>current.map(row=>row.id===id?{...row,[key]:value}:row))
  async function submit(){setSaving(true);setError('');try{const openingDate=String(loan.private_details?.record_date??'');const items=await addPrivateLoanPriorPayments(loan.id,{items:rows.map(row=>({amount:Number(row.amount),payment_date:dateWithinPreOpeningYear(row.year,openingDate),source:row.source,note:row.note})),idempotency_key:crypto.randomUUID()});onAdded(items);setRows([newRow()])}catch(e){setError(t(e instanceof Error?e.message:'Unable to save the loan.'))}finally{setSaving(false)}}
  return <section className="prior-payment-details">
    <header><div><h4>{t('Pre-opening payment details')}</h4><p>{t('Informational breakdown only. It does not reduce the current loan balance again.')}</p></div><button type="button" onClick={()=>setOpen(value=>!value)}>{open?<X size={14}/>:<Plus size={14}/>} {t(open?'Close':'Add detail')}</button></header>
    <div className="prior-payment-details__progress"><span>{t('Detailed')} <strong>{recorded.toLocaleString()}</strong></span><span>{t('Remaining to detail')} <strong>{remaining.toLocaleString()}</strong></span></div>
    {open&&<div className="prior-payment-details__editor">{rows.map(row=><div className="prior-payment-details__form" key={row.id}><label><span>{t('Payment year')}</span><input type="number" min="1900" max={Number(String(loan.private_details?.record_date).slice(0,4))} value={row.year} onChange={e=>update(row.id,'year',e.target.value)}/></label><label><span>{t('Amount')}</span><input inputMode="decimal" value={displayAmountInput(row.amount,language)} onChange={e=>update(row.id,'amount',parseAmountInput(e.target.value))}/></label><label><span>{t('Payment source')}</span><input value={row.source} onChange={e=>update(row.id,'source',e.target.value)}/></label><label><span>{t('Notes')}</span><input value={row.note} onChange={e=>update(row.id,'note',e.target.value)}/></label>{rows.length>1&&<button className="prior-payment-details__remove" type="button" aria-label={t('Remove')} onClick={()=>setRows(current=>current.filter(item=>item.id!==row.id))}><Trash2 size={14}/></button>}</div>)}<footer className="prior-payment-details__actions"><button type="button" onClick={()=>setRows(current=>[...current,newRow()])}><Plus size={14}/>{t('Add another payment')}</button><span>{error||`${t('Batch total')}: ${total.toLocaleString()} · ${rows.length} ${t('payments')}`}</span><button disabled={saving||!valid} type="button" onClick={submit}>{t('Save all details')}</button></footer></div>}
  </section>
}
