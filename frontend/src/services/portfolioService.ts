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
}

export async function updateMarketPrices(): Promise<MarketPriceUpdateResult> {
  return apiPost<MarketPriceUpdateResult>(
    '/investing/market-prices/update',
    {},
  )
}
