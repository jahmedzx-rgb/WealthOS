import { useEffect, useState } from 'react'

import {
  getPortfolios,
  type PortfolioLookup,
} from '../services/portfolioService'

export function usePortfolios() {
  const [portfolios, setPortfolios] = useState<
    PortfolioLookup[]
  >([])

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState('')

  async function load() {
      try {
        const data = await getPortfolios()

        setPortfolios(data)
      } catch (error) {
        if (error instanceof Error) {
          setError(error.message)
        } else {
          setError('Failed to load portfolios.')
        }
      } finally {
        setLoading(false)
      }
  }
  useEffect(() => {
    // Loading an external API is the synchronization this effect owns.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    load()
  }, [])

  return {
    portfolios,
    loading,
    error,
    refresh: load,
  }
}
