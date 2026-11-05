import { useCallback, useEffect, useRef, useState } from 'react'

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
  const hasLoaded = useRef(false)

  const refresh = useCallback(async () => {
    if (portfolioId === null) {
      setData(null)
      setLoading(false)
      return
    }
    if (!hasLoaded.current) setLoading(true)
    setError(null)
    try {
      setData(await getPortfolioSummary(portfolioId))
    } catch (requestError) {
      if (!hasLoaded.current) setError(requestError instanceof Error ? requestError.message : 'Unable to load portfolio.')
    } finally {
      hasLoaded.current = true
      setLoading(false)
    }
  }, [portfolioId])

  useEffect(() => {
    hasLoaded.current = false
    queueMicrotask(() => void refresh())
  }, [refresh])

  return {
    data,
    loading,
    error,
    refresh,
  }
}
