import { useEffect, useState } from 'react'
import { getFinancialSummary, type FinancialSummary } from '../services/accountingService'

export function useFinancialSummary() {
  const [data, setData] = useState<FinancialSummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const refresh = () => getFinancialSummary().then(setData).catch((reason: unknown)=>setError(reason instanceof Error ? reason.message : 'Unable to load financial summary.')).finally(()=>setLoading(false))
  useEffect(() => { void refresh() }, [])
  return { data, loading, error, refresh }
}
