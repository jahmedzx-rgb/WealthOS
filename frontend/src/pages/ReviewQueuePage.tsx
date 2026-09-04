/* eslint-disable react-hooks/set-state-in-effect */
import { useEffect, useState } from 'react'
import { ArrowRight, CheckCircle2, FileSpreadsheet, TriangleAlert, EyeOff, Trash2, X } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import PageNavigation from '../components/ui/PageNavigation'
import { useLanguage } from '../context/LanguageContext'
import { deleteImportBatch, getPendingImportBatches, updateImportedOperation, type SavedImportBatch, type SavedImportOperation } from '../services/importReviewService'
import { formatDisplayInteger, formatDisplayNumber, formatDisplayPercent } from '../utils/localeFormat'
import './ReviewQueuePage.css'
import './ReviewQueueActions.css'

type QueueItem=SavedImportOperation&{filename:string}
const routeFor=(type:string)=>type==='Income'?'/operations/income':type==='Transfer'?'/operations/transfer':type==='Card payment'?'/operations/card-payment':type==='Trade'?'/operations/trade':type==='Expense'?'/operations/expense':type==='Deposit'?'/operations/deposit':type==='Property'?'/operations/property':'/operations'

export default function ReviewQueuePage(){
  const{direction,language,t}=useLanguage()
  const navigate=useNavigate()
  const[batches,setBatches]=useState<SavedImportBatch[]>([])
  const[loading,setLoading]=useState(true)
  const[error,setError]=useState('')
  const[deleting,setDeleting]=useState<SavedImportBatch|null>(null)
  const[deleteBusy,setDeleteBusy]=useState(false)
  async function load(){setLoading(true);setError('');try{setBatches(await getPendingImportBatches())}catch(reason){setError(t(reason instanceof Error?reason.message:'Unable to load review queue.'))}finally{setLoading(false)}}
  useEffect(()=>{void load()},[])
  const items:QueueItem[]=batches.flatMap(batch=>batch.operations.filter(item=>item.status==='PENDING').map(item=>({...item,filename:batch.filename})))
  async function ignore(item:QueueItem){await updateImportedOperation(item.id,'IGNORED');setBatches(current=>current.map(batch=>({...batch,operations:batch.operations.map(operation=>operation.id===item.id?{...operation,status:'IGNORED'}:operation)})).filter(batch=>batch.operations.some(operation=>operation.status==='PENDING')))}
  async function removeDocument(){if(!deleting)return;setDeleteBusy(true);setError('');try{await deleteImportBatch(deleting.id);setBatches(current=>current.filter(batch=>batch.id!==deleting.id));setDeleting(null)}catch(reason){setError(t(reason instanceof Error?reason.message:'The document could not be deleted.'));setDeleting(null)}finally{setDeleteBusy(false)}}
  return <section className="review-queue">
    <header><div><p>{t('Accounting workspace')}</p><h1>{t('Review Queue')}</h1><span>{t('Review imported operations before they are posted to the General Ledger.')}</span></div><PageNavigation/></header>
    <div className="review-queue__stats"><article><span>{t('Pending review')}</span><strong>{formatDisplayInteger(items.length,language)}</strong><small>{t('Across')} {formatDisplayInteger(batches.length,language)} {t('files')}</small></article><article><span>{t('High confidence')}</span><strong>{formatDisplayInteger(items.filter(item=>item.confidence>=80).length,language)}</strong><small>{t('Ready for confirmation')}</small></article><article><span>{t('Reminders due')}</span><strong>{formatDisplayInteger(batches.filter(batch=>batch.reminder_due).length,language)}</strong><small>{t('Every 3 days')}</small></article></div>
    <section className="review-queue__panel"><div className="review-queue__head"><div><h2>{t('Imported operations')}</h2><p>{t('Drafts only — nothing below has been posted.')}</p></div><button type="button" onClick={()=>void load()}>{t('Refresh')}</button></div>
      {loading?<p>{t('Loading review queue…')}</p>:error?<p className="review-queue__error">{error}</p>:!items.length?<div className="review-queue__empty"><CheckCircle2 size={22}/><strong>{t('No pending operations')}</strong><span>{t('Your review queue is clear.')}</span></div>:<div className="review-queue__files">{batches.map(batch=>{const pendingItems=batch.operations.filter(item=>item.status==='PENDING').map(item=>({...item,filename:batch.filename}));if(!pendingItems.length)return null;return <section key={batch.id}><header><span><FileSpreadsheet size={15}/><strong>{batch.filename}</strong><small>{formatDisplayInteger(pendingItems.length,language)} {t('awaiting review')}</small></span><button type="button" onClick={()=>setDeleting(batch)}><Trash2 size={13}/>{t('Delete File')}</button></header><div className="review-queue__list">{pendingItems.map(item=><article key={item.id}><span className="review-queue__file"><FileSpreadsheet size={17}/></span><div><strong>{t(item.operation_type)}</strong><small>{item.description}</small></div><div><strong>{item.amount===null?t('Amount not found'):`${item.currency??''} ${formatDisplayNumber(item.amount,undefined,language)}`.trim()}</strong><small>{formatDisplayPercent(item.confidence,0,language)} {t('confidence')}</small></div><i className={item.confidence<80?'is-warning':''}>{item.confidence<80?<><TriangleAlert size={13}/>{t('Needs attention')}</>:<><CheckCircle2 size={13}/>{t('Ready')}</>}</i><span className="review-queue__actions"><button className="is-ignore" type="button" onClick={()=>void ignore(item)}><EyeOff size={13}/>{t('Ignore')}</button><button type="button" onClick={()=>navigate(routeFor(item.operation_type),{state:{importedOperation:item}})}>{t('Review')} <ArrowRight size={14} style={direction==='rtl'?{transform:'rotate(180deg)'}:undefined}/></button></span></article>)}</div></section>})}</div>}
    </section>
    {deleting&&<div className="review-delete-modal" role="dialog" aria-modal="true" aria-labelledby="queue-delete-title" onMouseDown={event=>{if(event.currentTarget===event.target&&!deleteBusy)setDeleting(null)}}><section><header><span><Trash2 size={18}/></span><div><h2 id="queue-delete-title">{t('Delete Imported File?')}</h2><p>{deleting.filename}</p></div><button type="button" aria-label={t('Close')} disabled={deleteBusy} onClick={()=>setDeleting(null)}><X size={16}/></button></header><div><strong>{t('All unposted operations from this file will leave the queue.')}</strong><p>{t('Previously posted accounting records and duplicate-protection fingerprints remain preserved.')}</p></div><footer><button type="button" disabled={deleteBusy} onClick={()=>setDeleting(null)}>{t('Keep File')}</button><button type="button" disabled={deleteBusy} onClick={()=>void removeDocument()}>{t(deleteBusy?'Deleting…':'Delete File')}</button></footer></section></div>}
  </section>
}
