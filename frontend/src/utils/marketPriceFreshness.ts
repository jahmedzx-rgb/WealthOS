export type MarketPriceFreshness = {
  status: string
  asOf: string
  ageMinutes: number
}

function parseMarketTimestamp(value: string) {
  const includesZone = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value)
  return new Date(includesZone ? value : `${value}Z`)
}

function isSaudiExchange(exchange?: string) {
  return ['SAUDI_EXCHANGE', 'TADAWUL'].includes(exchange?.toUpperCase() ?? '')
}

function zonedMarketParts(now: Date, timeZone: string) {
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone, weekday: 'short', hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
  }).formatToParts(now)
  const part = (type: Intl.DateTimeFormatPartTypes) => parts.find(item => item.type === type)?.value ?? ''
  return { weekday:part('weekday'), minutes:Number(part('hour')) * 60 + Number(part('minute')) }
}

function isTrackedMarketOpen(now: Date, exchange?: string) {
  const normalized = exchange?.toUpperCase() ?? ''
  if (isSaudiExchange(normalized)) {
    const {weekday,minutes}=zonedMarketParts(now,'Asia/Riyadh')
    return !['Fri','Sat'].includes(weekday)&&minutes>=10*60&&minutes<15*60
  }
  if (['NASDAQ','NYSE','AMEX'].includes(normalized)) {
    const {weekday,minutes}=zonedMarketParts(now,'America/New_York')
    return !['Sat','Sun'].includes(weekday)&&minutes>=9*60+30&&minutes<16*60
  }
  return null
}

function normalizedExchangeTimestamp(timestamp: Date, exchange?: string) {
  if (!isSaudiExchange(exchange)) return timestamp
  const weekday = new Intl.DateTimeFormat('en-US', { timeZone: 'Asia/Riyadh', weekday: 'short' }).format(timestamp)
  const daysBack = weekday === 'Fri' ? 1 : weekday === 'Sat' ? 2 : 0
  if (!daysBack) return timestamp
  const corrected = new Date(timestamp)
  corrected.setUTCDate(corrected.getUTCDate() - daysBack)
  corrected.setUTCHours(12, 0, 0, 0)
  return corrected
}

export function marketPriceFreshness(value: string, now = new Date(), exchange?: string): MarketPriceFreshness {
  const timestamp = normalizedExchangeTimestamp(parseMarketTimestamp(value), exchange)
  if (Number.isNaN(timestamp.getTime())) return { status: 'Price Time Unavailable', asOf: 'Unknown', ageMinutes: 0 }
  const ageMinutes = Math.max(0, Math.floor((now.getTime() - timestamp.getTime()) / 60000))
  const sameLocalDay = timestamp.toLocaleDateString('en-CA') === now.toLocaleDateString('en-CA')
  const marketOpen=isTrackedMarketOpen(now,exchange)
  const status = marketOpen === false
    ? 'Market Closed'
    : ageMinutes <= 1
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
    const freshness=oldest?marketPriceFreshness(oldest,undefined,positions[0].exchange):null
    return freshness?`${exchanges[0]} · ${freshness.status} · As Of ${freshness.asOf}`:`${exchanges[0]} · Price Time Unavailable`
  }
  return `${exchanges.length} Markets · Latest Available By Exchange · ${exchanges.join(' + ')}`
}

export function marketPriceCoverageLabels(positions:MarketPricedPosition[]){
  if(!positions.length)return['No Market Prices Yet']
  const grouped=new Map<string,MarketPricedPosition[]>()
  positions.forEach(position=>{const name=marketName(position.exchange);grouped.set(name,[...(grouped.get(name)??[]),position])})
  return [...grouped.entries()].map(([name,items])=>{
    const oldest=oldestMarketPriceTimestamp(items.map(item=>item.market_price_date))
    const freshness=oldest?marketPriceFreshness(oldest,undefined,items[0].exchange):null
    return freshness?`${name} · ${freshness.status} · As Of ${freshness.asOf}`:`${name} · Price Time Unavailable`
  })
}
