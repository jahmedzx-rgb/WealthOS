import { useEffect, useState } from 'react'

import { getPositionDetail } from '../services/portfolioService'
import type { PortfolioPosition } from '../types/portfolio'

export function usePosition(
  portfolioId: number,
  securityId: number,
) {
  const [data, setData] =
    useState<PortfolioPosition | null>(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState<string | null>(null)

  useEffect(() => {
    async function loadPosition() {
      try {
        const result = await getPositionDetail(
          portfolioId,
          securityId,
        )

        setData(result)
      } catch (requestError) {
        setError(
          requestError instanceof Error
            ? requestError.message
            : 'Unable to load position.',
        )
      } finally {
        setLoading(false)
      }
    }

    void loadPosition()
  }, [portfolioId, securityId])

  return {
    data,
    loading,
    error,
  }
}
