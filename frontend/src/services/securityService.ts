import { apiGet, apiPost } from './api'

export type SecurityLookup = {
  id: number
  symbol: string
  name: string
  name_ar?: string | null
  name_en?: string | null
  exchange: string | null
  currency_code: string
  market_symbol: string | null
  security_type?: 'STOCK'|'ETF'|'REIT'
}

export type MarketSecurityResult=Omit<SecurityLookup,'id'>&{id:number|null;registered:boolean;owned:boolean;security_type:'STOCK'|'ETF'|'REIT';market_symbol:string}

export async function getSecurities(): Promise<
  SecurityLookup[]
> {
  return apiGet<SecurityLookup[]>(
    '/investing/securities',
  )
}

export function createSaudiSecurity(input:{symbol:string;name:string;security_type:'STOCK'|'ETF'|'REIT'}){
  return apiPost<SecurityLookup>('/investing/securities/saudi',input)
}

export function searchMarketSecurities(query:string){return apiGet<MarketSecurityResult[]>(`/investing/securities/search?query=${encodeURIComponent(query)}`)}
export function registerMarketSecurity(input:Omit<MarketSecurityResult,'id'|'registered'|'owned'>){return apiPost<SecurityLookup>('/investing/securities/register',input)}
export type DistributionFrequency='WEEKLY'|'MONTHLY'|'QUARTERLY'|'SEMI_ANNUAL'|'ANNUAL'|'IRREGULAR'
export type DistributionPreview={available:boolean;distribution_date?:string;eligibility_date?:string|null;amount_per_unit?:number;source?:string;date_kind?:'payment'|'eligibility';frequency?:DistributionFrequency;sources_checked:string[]}
export function getNextDistribution(securityId:number){return apiGet<DistributionPreview>(`/investing/securities/${securityId}/next-distribution`)}
