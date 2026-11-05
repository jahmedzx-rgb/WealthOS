import { apiGet, apiPost } from './api'

const insightRequests=new Map<string,Promise<unknown>>()
function cachedInsight<T>(key:string,ttl:number,request:()=>Promise<T>):Promise<T>{
  try{const raw=localStorage.getItem(key);if(raw){const saved=JSON.parse(raw) as {expires:number;value:T};if(saved.expires>Date.now())return Promise.resolve(saved.value);localStorage.removeItem(key)}}catch{/* ignore an unavailable cache */}
  const active=insightRequests.get(key) as Promise<T>|undefined
  if(active)return active
  const pending=request().then(value=>{try{localStorage.setItem(key,JSON.stringify({expires:Date.now()+ttl,value}))}catch{/* cache capacity must not block data */}return value}).finally(()=>insightRequests.delete(key))
  insightRequests.set(key,pending)
  return pending
}

export type SecurityLookup = {
  id: number
  symbol: string
  name: string
  name_ar?: string | null
  name_en?: string | null
  exchange: string | null
  currency_code: string
  market_symbol: string | null
  security_type?: 'STOCK'|'ETF'|'REIT'|'MUTUAL_FUND'|'OPTION'
}

export type MarketSecurityResult=Omit<SecurityLookup,'id'>&{id:number|null;registered:boolean;owned:boolean;security_type:'STOCK'|'ETF'|'REIT'|'OPTION';market_symbol:string}

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
export type DividendYieldResult={available:boolean;dividend_yield?:number;trailing_distribution_per_unit?:number;price?:number;distribution_frequency?:DistributionFrequency|null;source:string}
export function getDividendYield(securityId:number){return cachedInsight(`wealthos:dividend-yield:${securityId}`,6*60*60*1000,()=>apiGet<DividendYieldResult>(`/investing/securities/${securityId}/dividend-yield`))}
export type AnalystFairValueResult={available:boolean;fair_value?:number;target_median?:number|null;target_high?:number|null;target_low?:number|null;recommendation?:string|null;analyst_count?:number|null;source:string}
export function getAnalystFairValue(securityId:number){return cachedInsight(`wealthos:analyst-value:${securityId}`,24*60*60*1000,()=>apiGet<AnalystFairValueResult>(`/investing/securities/${securityId}/analyst-fair-value`))}
