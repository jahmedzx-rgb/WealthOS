import { apiDelete, apiGet, apiPatch, apiPost } from './api'

import type {
  PortfolioPosition,
  PortfolioSummary,
} from '../types/portfolio'

export type PortfolioLookup = {
  id: number
  name: string
  broker_id: number | null
  broker_name: string | null
  portfolio_number_last4: string | null
  iban_last4: string | null
  cash_balance: number
  base_currency_code: string
}

export async function getPortfolios(): Promise<
  PortfolioLookup[]
> {
  return apiGet<PortfolioLookup[]>(
    '/portfolios',
  )
}

export function createPortfolio(input: { name: string; broker_id: number; portfolio_number: string; iban?: string; description?: string; currency_code?: string }) {
  return apiPost<PortfolioLookup>('/portfolios', input)
}

export function recordOpeningPortfolioBalance(portfolioId:number,input:{cash_balance:number;as_of_date:string;positions:Array<{security_id:number;quantity:number;total_cost:number;market_price:number}>}){
  return apiPost<{portfolio_id:number;positions_count:number;cash_balance:number;journal_entry_id:number}>(`/portfolios/${portfolioId}/opening-balance`,input)
}
export function correctOpeningPortfolioBalance(portfolioId:number,input:{cash_balance:number;as_of_date:string;positions:Array<{security_id:number;quantity:number;total_cost:number;market_price:number}>}){
  return apiPatch<{portfolio_id:number;cash_balance:number;journal_entry_id:number}>(`/portfolios/${portfolioId}/opening-balance`,input)
}

export function updatePortfolio(id:number,input:{name:string;portfolio_number?:string;iban?:string;currency_code:string}){return apiPatch<PortfolioLookup>(`/portfolios/${id}`,input)}
export function removePortfolio(id:number){return apiDelete(`/portfolios/${id}`)}

export async function getPortfolioSummary(
  portfolioId: number | 'consolidated',
): Promise<PortfolioSummary> {
  return apiGet<PortfolioSummary>(
    `/portfolios/${portfolioId}/summary`,
  )
}

export type PortfolioPerformanceHistory = {
  period: '1W' | '1M' | '1Y' | 'YTD'
  has_sufficient_history: boolean
  change: number
  percentage: number
  points: Array<{ date: string; market_value: number; total_cost: number; total_return: number }>
}

export function getPortfolioPerformanceHistory(portfolioId: number, period: PortfolioPerformanceHistory['period']) {
  return apiGet<PortfolioPerformanceHistory>(`/portfolios/${portfolioId}/performance-history?period=${period}`)
}

export function getConsolidatedPerformanceHistory(period: PortfolioPerformanceHistory['period']) {
  return apiGet<PortfolioPerformanceHistory>(`/portfolios/consolidated/performance-history?period=${period}`)
}

export type PortfolioMonthEndPosition={portfolio_id:number;portfolio_name:string;security_id:number;symbol:string;name:string;security_type:string;currency_code:string;quantity:number;average_cost:number;total_cost:number;market_price:number|null;market_price_date:string|null;market_value:number|null;unrealized_pl:number|null;total_cost_base:number;market_value_base:number|null;unrealized_pl_base:number|null}
export type PortfolioMonthEnd={available:boolean;year:number;month:number;as_of_date?:string;valuation_snapshot_date?:string;market_value?:number;total_cost?:number;unrealized_pl?:number;total_return?:number;positions?:PortfolioMonthEndPosition[];historical_portfolio_ids?:number[];positions_complete?:boolean;missing_symbols?:string[]}
export function getConsolidatedMonthEnd(year:number,month:number){return apiGet<PortfolioMonthEnd>(`/portfolios/consolidated/month-end?year=${year}&month=${month}`)}
export function getPortfolioMonthEnd(portfolioId:number,year:number,month:number){return apiGet<PortfolioMonthEnd>(`/portfolios/${portfolioId}/month-end?year=${year}&month=${month}`)}

export async function getPositionDetail(
  portfolioId: number,
  securityId: number,
): Promise<PortfolioPosition> {
  return apiGet<PortfolioPosition>(
    `/portfolios/${portfolioId}/positions/${securityId}`,
  )
}

export function updatePositionFairValue(portfolioId: number, securityId: number, fairValue: number | null) {
  return apiPatch<{ portfolio_id:number; security_id:number; fair_value:number|null }>(`/portfolios/${portfolioId}/positions/${securityId}`, { fair_value: fairValue })
}

export type MarketPriceUpdateResult = {
  updated_count: number
  failed_count?: number
  failed_security_ids?: number[]
  failed_quotes?: Array<{security_id:number;symbol:string;message:string}>
}

const marketPriceUpdatesInFlight = new Map<string, Promise<MarketPriceUpdateResult>>()
const marketPriceUpdatesCompletedAt = new Map<string, number>()

export function updateMarketPrices(securityIds?: number[]): Promise<MarketPriceUpdateResult> {
  const ids = securityIds ? [...new Set(securityIds)].sort((left, right) => left - right) : null
  const key = ids ? ids.join(',') : '*'
  const inFlight = marketPriceUpdatesInFlight.get(key)
  if (inFlight) return inFlight

  if (ids?.length) {
    const completedAt = marketPriceUpdatesCompletedAt.get(key) ?? 0
    if (Date.now() - completedAt < 30_000) {
      return Promise.resolve({ updated_count: 0, failed_count: 0, failed_security_ids: [] })
    }
  }

  const query = new URLSearchParams()
  ids?.forEach(id => query.append('security_ids', String(id)))
  const path = `/investing/market-prices/update${ids ? `?${query.toString()}` : ''}`
  const request = apiPost<MarketPriceUpdateResult>(path, {})
  marketPriceUpdatesInFlight.set(key, request)
  void request.then(
    () => { if (ids?.length) marketPriceUpdatesCompletedAt.set(key, Date.now()) },
    () => undefined,
  ).finally(() => {
    if (marketPriceUpdatesInFlight.get(key) === request) marketPriceUpdatesInFlight.delete(key)
  })
  return request
}
