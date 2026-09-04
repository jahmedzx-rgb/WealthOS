import { apiDelete, apiGet, apiPatch, apiPost } from './api'

export type BrokerLookup = {
  id: number
  code: string
  name: string
  country: string | null
  website: string | null
  institution_name: string
  execution_partner: string|null
  commission_rate: number | null
  commission_source: string | null
  commission_tax_rate: number | null
  commission_tax_source: string | null
  dividend_withholding_tax_rate: number|null
  dividend_withholding_tax_source: string | null
}

export async function getBrokers(): Promise<
  BrokerLookup[]
> {
  return apiGet<BrokerLookup[]>(
    '/investing/brokers',
  )
}

export type BrokerCatalogItem = {
  name: string
  country: string
  website: string
  aliases: string[]
  default_commission_rate: number | null
  commission_source: string | null
  default_commission_tax_rate: number | null
  commission_tax_source: string | null
  institution_name: string
  execution_partner: string|null
}

export function getBrokerCatalog() {
  return apiGet<BrokerCatalogItem[]>('/investing/brokers/catalog')
}

export function createBroker(input: {
  name: string
  country?: string
  website?: string
  commission_rate?: number
  commission_tax_rate?: number
  dividend_withholding_tax_rate?: number|null
}) {
  return apiPost<BrokerLookup>(
    '/investing/brokers',
    input,
  )
}

export function updateBrokerCommission(id:number,commission_rate:number,commission_tax_rate:number,dividend_withholding_tax_rate:number|null,website?:string){
  const input:{commission_rate:number;commission_tax_rate:number;dividend_withholding_tax_rate:number|null;website?:string|null}={commission_rate,commission_tax_rate,dividend_withholding_tax_rate}
  if(website!==undefined)input.website=website.trim()||null
  return apiPatch<{id:number;website:string|null;commission_rate:number;commission_source:string;commission_tax_rate:number;commission_tax_source:string;dividend_withholding_tax_rate:number;dividend_withholding_tax_source:string}>(`/investing/brokers/${id}/commission`,input)
}

export function closeBroker(id:number){return apiDelete(`/investing/brokers/${id}`)}
