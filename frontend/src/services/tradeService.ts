import { apiPost } from './api'

export type TradeRequest = {
  portfolio_id: number
  broker_id: number
  security_id: number

  side:
    | 'BUY'
    | 'SELL'

  quantity: number
  price: number
  commission: number
  trade_date: string
  next_distribution_date?: string
  expected_distribution_amount?: number
  distribution_frequency?: string
  fair_value?: number
}

export async function createTrade(
  request: TradeRequest,
) {
  return apiPost(
    '/investing/trades',
    request,
  )
}
