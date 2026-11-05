import { useEffect, useMemo, useRef } from 'react'

import { updateMarketPrices, type MarketPriceUpdateResult } from '../services/portfolioService'
import type { PortfolioPosition } from '../types/portfolio'

export function usePortfolioPriceSync(
  positions: PortfolioPosition[] | undefined,
  refresh: () => Promise<void>,
  enabled = true,
  onUpdateResult?: (result:MarketPriceUpdateResult)=>void,
) {
  const onUpdateResultRef=useRef(onUpdateResult)
  useEffect(()=>{onUpdateResultRef.current=onUpdateResult},[onUpdateResult])
  const securityKey = useMemo(
    () => [...new Set((positions ?? []).map(position => position.security_id))].sort((left, right) => left - right).join(','),
    [positions],
  )

  useEffect(() => {
    if (!enabled || !securityKey) return

    const securityIds = securityKey.split(',').map(Number)
    let active = true
    let updating = false

    const syncPrices = async () => {
      if (updating || document.visibilityState === 'hidden') return
      updating = true
      try {
        const result = await updateMarketPrices(securityIds)
        if (!active) return
        onUpdateResultRef.current?.(result)
        if (result.updated_count > 0) await refresh()
      } catch {
        if (active) onUpdateResultRef.current?.({updated_count:0,failed_count:securityIds.length,failed_security_ids:securityIds})
      } finally {
        updating = false
      }
    }

    void syncPrices()
    const interval = window.setInterval(() => void syncPrices(), 120_000)
    window.addEventListener('focus', syncPrices)
    document.addEventListener('visibilitychange', syncPrices)

    return () => {
      active = false
      window.clearInterval(interval)
      window.removeEventListener('focus', syncPrices)
      document.removeEventListener('visibilitychange', syncPrices)
    }
  }, [enabled, refresh, securityKey])
}
