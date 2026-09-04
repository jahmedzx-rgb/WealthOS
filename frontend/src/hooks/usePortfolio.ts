import { useCallback, useEffect, useState } from 'react'

import { getPortfolioSummary } from '../services/portfolioService'
import type { PortfolioSummary } from '../types/portfolio'

export function usePortfolio(
  portfolioId: number | 'consolidated' | null,
) {
  const [data, setData] =
    useState<PortfolioSummary | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  const refresh = useCallback(async () => {
    if (portfolioId === null) {
      setData(null)
      setLoading(false)
      return
    }
    setLoading(true)
    setError(null)
    try {
      setData(await getPortfolioSummary(portfolioId))
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Unable to load portfolio.')
    } finally {
      setLoading(false)
    }
  }, [portfolioId])

  useEffect(() => { queueMicrotask(() => void refresh()) }, [refresh])

  return {
    data,
    loading,
    error,
    refresh,
  }
}
