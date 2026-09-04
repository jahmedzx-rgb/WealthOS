export type MarketPriceFreshness = {
  status: string
  asOf: string
  ageMinutes: number
}

function parseMarketTimestamp(value: string) {
  const includesZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(includesZone ? value : `${value}Z`)
}

export function marketPriceFreshness(value: string, now = new Date()): MarketPriceFreshness {
  const timestamp = parseMarketTimestamp(value)
  if (Number.isNaN(timestamp.getTime())) return { status: 'Price Time Unavailable', asOf: 'Unknown', ageMinutes: 0 }
  const ageMinutes = Math.max(0, Math.floor((now.getTime() - timestamp.getTime()) / 60000))
  const sameLocalDay = timestamp.toLocaleDateString('en-CA') === now.toLocaleDateString('en-CA')
  const status = ageMinutes <= 1
    ? 'Live'
    : ageMinutes < 60
      ? `Delayed · ${ageMinutes} Min`
      : sameLocalDay
        ? `Delayed · ${Math.floor(ageMinutes / 60)} Hr`
        : 'Previous Close'
  const asOf = timestamp.toLocaleString('en-GB', { day:'2-digit', month:'2-digit', year:'numeric', hour:'2-digit', minute:'2-digit' })
  return { status, asOf, ageMinutes }
}

export function oldestMarketPriceTimestamp(values: string[]) {
  return values.reduce<string | null>((oldest, value) => {
    if (!oldest) return value
    return parseMarketTimestamp(value).getTime() < parseMarketTimestamp(oldest).getTime() ? value : oldest
  }, null)
}

type MarketPricedPosition = { exchange:string;market_price_date:string }

export function marketName(exchange:string){
  const names:Record<string,string>={SAUDI_EXCHANGE:'Saudi Exchange',TADAWUL:'Saudi Exchange',NASDAQ:'Nasdaq',NYSE:'New York Stock Exchange',AMEX:'NYSE American'}
  return names[exchange.toUpperCase()]??exchange.replaceAll('_',' ')
}

export function marketPriceCoverageLabel(positions:MarketPricedPosition[]){
  if(!positions.length)return'No Market Prices Yet'
  const exchanges=[...new Set(positions.map(item=>marketName(item.exchange)))]
  if(exchanges.length===1){
    const oldest=oldestMarketPriceTimestamp(positions.map(item=>item.market_price_date))
    const freshness=oldest?marketPriceFreshness(oldest):null
    return freshness?`${exchanges[0]} · ${freshness.status} · As Of ${freshness.asOf}`:`${exchanges[0]} · Price Time Unavailable`
  }
  return `${exchanges.length} Markets · Latest Available By Exchange · ${exchanges.join(' + ')}`
}
