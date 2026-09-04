import { useEffect, useState } from 'react'

import {
  getBrokers,
  type BrokerLookup,
} from '../services/brokerService'

export function useBrokers() {
  const [brokers, setBrokers] = useState<
    BrokerLookup[]
  >([])

  const [loading, setLoading] = useState(true)

  const [error, setError] = useState('')

  useEffect(() => {
    async function load() {
      try {
        const data = await getBrokers()

        setBrokers(data)
      } catch (error) {
        if (error instanceof Error) {
          setError(error.message)
        } else {
          setError('Failed to load brokers.')
        }
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [])

  return {
    brokers,
    loading,
    error,
  }
}