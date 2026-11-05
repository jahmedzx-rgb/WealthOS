import { useCallback, useEffect, useState } from 'react'
import { getFinancialSummary, type FinancialSummary } from '../services/accountingService'

let cachedSummary:FinancialSummary|null=null
let cachedAt=0
let pendingSummary:Promise<FinancialSummary>|null=null
const cacheDuration=30_000

function loadSummary(force=false){
  if(pendingSummary)return pendingSummary
  if(!force&&cachedSummary&&Date.now()-cachedAt<cacheDuration)return Promise.resolve(cachedSummary)
  pendingSummary=getFinancialSummary().then(value=>{cachedSummary=value;cachedAt=Date.now();return value}).finally(()=>{pendingSummary=null})
  return pendingSummary
}

export function useFinancialSummary(refreshOnFocus=false) {
  const [data, setData] = useState<FinancialSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const refresh = useCallback(() => loadSummary(true).then(setData).catch((reason: unknown)=>setError(reason instanceof Error ? reason.message : 'Unable to load financial summary.')).finally(()=>setLoading(false)),[])
  useEffect(() => {
    let active=true
    const load=()=>{void loadSummary(refreshOnFocus).then(value=>{if(active)setData(value)}).catch((reason: unknown)=>{if(active)setError(reason instanceof Error ? reason.message : 'Unable to load financial summary.')}).finally(()=>{if(active)setLoading(false)})}
    const refreshWhenVisible=()=>{if(document.visibilityState==='visible')void refresh()}
    load()
    if(refreshOnFocus){window.addEventListener('focus',refreshWhenVisible);document.addEventListener('visibilitychange',refreshWhenVisible)}
    return()=>{active=false;window.removeEventListener('focus',refreshWhenVisible);document.removeEventListener('visibilitychange',refreshWhenVisible)}
  },[refresh,refreshOnFocus])
  return { data, loading, error, refresh }
}
