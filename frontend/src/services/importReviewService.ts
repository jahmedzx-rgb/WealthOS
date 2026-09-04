import { apiDelete, apiGet, apiPatch, apiPost } from './api'
import type { ExtractedOperation } from './documentImportService'

export type SavedImportOperation = { id:number; operation_type:string; description:string; amount:number|null; currency:string|null; transaction_date:string|null; card_last4:string|null; confidence:number; source_text:string; status:string; matched_entity_type:string|null; matched_entity_id:number|null; posting_reference:string|null; posted_at:string|null }
export type SavedImportBatch = { id:number; filename:string; file_size:number; file_type:string; status:string; created_at:string; next_reminder_at:string; reminder_due:boolean; operations:SavedImportOperation[] }

export function saveImportBatch(file:File,operations:ExtractedOperation[],_confirmedIds:string[],ignoredIds:string[]){return apiPost<SavedImportBatch>('/imports/batches',{filename:file.name,file_size:file.size,file_type:file.type,operations:operations.map((item)=>({operation_type:item.type,description:item.description,amount:item.amount,currency:item.currency,transaction_date:item.date,card_last4:item.cardLast4,confidence:item.confidence,source_text:item.sourceText,status:ignoredIds.includes(item.id)?'IGNORED':'PENDING'}))})}
export function getPendingImportBatches(){return apiGet<SavedImportBatch[]>('/imports/batches/pending')}
export function getImportBatches(){return apiGet<SavedImportBatch[]>('/imports/batches')}
export function deleteImportBatch(id:number){return apiDelete(`/imports/batches/${id}`)}
export function updateImportedOperation(id:number,status:'IGNORED'){return apiPatch<{id:number;status:string}>(`/imports/operations/${id}/${status}`)}
export function confirmImportedOperation(id:number,postingReference:string,matchedEntityType?:string,matchedEntityId?:number){return apiPost<{id:number;status:string;posting_reference:string}>(`/imports/operations/${id}/confirm`,{posting_reference:postingReference,matched_entity_type:matchedEntityType,matched_entity_id:matchedEntityId})}
