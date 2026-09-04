import { useLocation } from 'react-router-dom'
import { confirmImportedOperation, type SavedImportOperation } from '../services/importReviewService'

type ImportLocationState={importedOperation?:SavedImportOperation}

export function toLocalDateTime(value:string|null|undefined){
  if(!value)return''
  const normalized=value.trim().replace(/\//g,'-')
  const parts=normalized.match(/^(\d{1,2})-(\d{1,2})-(\d{2,4})$/)
  const iso=parts?`${parts[3].length===2?`20${parts[3]}`:parts[3]}-${parts[2].padStart(2,'0')}-${parts[1].padStart(2,'0')}T12:00`:normalized.length===10?`${normalized}T12:00`:normalized
  const date=new Date(iso)
  if(Number.isNaN(date.getTime()))return''
  return new Date(date.getTime()-date.getTimezoneOffset()*60000).toISOString().slice(0,16)
}

export function useImportedOperationDraft(){
  const location=useLocation()
  const draft=(location.state as ImportLocationState|null)?.importedOperation??null
  async function confirm(postingReference:string,matchedEntityType?:string,matchedEntityId?:number){
    if(!draft)return
    await confirmImportedOperation(draft.id,postingReference,matchedEntityType,matchedEntityId)
  }
  return{draft,confirm}
}

export function postingReference(result:unknown,fallback:string){
  if(result&&typeof result==='object'){
    const value=result as Record<string,unknown>
    const reference=value.related_reference??value.reference??value.journal_entry_id??value.trade_id??value.id
    if(reference!==undefined&&reference!==null)return `${fallback}:${String(reference)}`
  }
  return `${fallback}:${new Date().toISOString()}`
}
