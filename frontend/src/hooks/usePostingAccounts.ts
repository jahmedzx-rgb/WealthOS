import { useEffect, useState } from 'react'
import { getPostingAccounts, type PostingAccount } from '../services/accountingService'

export function usePostingAccounts() {
  const [accounts,setAccounts]=useState<PostingAccount[]>([])
  const [loading,setLoading]=useState(true)
  const [error,setError]=useState('')
  useEffect(()=>{getPostingAccounts().then(setAccounts).catch((reason:unknown)=>setError(reason instanceof Error?reason.message:'Unable to load accounts.')).finally(()=>setLoading(false))},[])
  return {accounts,loading,error}
}
