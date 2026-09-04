export type PositionTrade = {
  id: number
  broker_id: number
  side: string
  quantity: number
  price: number
  commission: number
  trade_date: string
}

export type PortfolioPosition = {
  portfolio_id?: number
  id?: number
  security_id: number
  symbol: string
  name: string
  security_type: string
  exchange: string
  currency_code: string
  quantity: number
  next_distribution_date: string | null
  expected_distribution_amount: number | null
  distribution_frequency: string | null
  fair_value: number | null
  average_cost: number
  total_cost: number
  market_price: number
  market_price_date: string
  market_value: number
  total_cost_base: number
  market_value_base: number
  unrealized_pl_base: number
  unrealized_pl: number
  weight: number
  trade_history: PositionTrade[]
}

export type PortfolioSummary = {
  portfolio: {
    id: number
    code: string
    name: string
    base_currency_id: number
    base_currency_code: string
    cash_balance: number
  }
  summary: {
    positions_count: number
    total_cost: number
    market_value: number
    unrealized_pl: number
    total_return: number
    total_return_percentage: number
  }
  allocation_summary: Record<string, number>
  positions: PortfolioPosition[]
}
