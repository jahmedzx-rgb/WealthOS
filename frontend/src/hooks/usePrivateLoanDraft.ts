import { useEffect, useRef, useState } from 'react'

export const emptyPrivateLoanDraft = () => ({mode:'OPENING' as 'OPENING'|'BANK'|'DIRECT_EXPENSE',name:'',lender:'',principal:'',extra:'0',paid:'0',date:'',dateText:'',bank:'',expense:'',beneficiary:'',note:'',key:crypto.randomUUID()})
export type PrivateLoanDraft = ReturnType<typeof emptyPrivateLoanDraft>

// Page memory only: survives in-app navigation, never browser storage/reopening.
const drafts = new Map<number, PrivateLoanDraft>()
if(typeof window!=='undefined') window.addEventListener('pagehide',()=>drafts.clear())

export function usePrivateLoanDraft(userId:number) {
  const [draft,setDraft]=useState(()=>drafts.get(userId)??emptyPrivateLoanDraft())
  const current=useRef(draft)
  useEffect(()=>{
    try {localStorage.removeItem(`wealthos:private-loan-draft:v1:${userId}`)} catch { /* No new drafts use browser storage. */ }
    const reset=()=>{drafts.delete(userId);const next=emptyPrivateLoanDraft();current.current=next;setDraft(next)}
    window.addEventListener('pagehide',reset)
    return()=>window.removeEventListener('pagehide',reset)
  },[userId])
  const update=<K extends keyof PrivateLoanDraft>(field:K,value:PrivateLoanDraft[K])=>{
    const next={...current.current,[field]:value}
    current.current=next;drafts.set(userId,next);setDraft(next)
  }
  const discard=()=>{drafts.delete(userId)}
  const clear=()=>{discard();const next=emptyPrivateLoanDraft();current.current=next;setDraft(next)}
  return {draft,update,clear,discard}
}
