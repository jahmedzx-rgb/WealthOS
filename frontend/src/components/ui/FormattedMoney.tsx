import { supportedCurrencies, useCurrency } from '../../context/CurrencyContext'
import type { Currency } from '../../context/CurrencyContext'
import CurrencyMark from './CurrencyMark'
import './FormattedMoney.css'

export default function FormattedMoney({ value, sign = '', currency: currencyOverride }: { value: string; sign?: string; currency?: Currency }) {
  const { currency: displayCurrency } = useCurrency()
  const currency = currencyOverride ?? displayCurrency
  const item = supportedCurrencies.find((candidate) => candidate.code === currency)
  const symbol = currency === 'SAR' ? '\u20C1' : item?.symbol ?? currency
  const symbolIndex = value.indexOf(symbol)

  if (symbolIndex < 0) return <>{value}</>

  const rawPrefix = value.slice(0, symbolIndex)
  const rawNumber = value.slice(symbolIndex + symbol.length).trimStart()
  const displayedSign = sign || (rawPrefix.includes('-') || rawNumber.startsWith('-') ? '-' : '')
  const prefix = rawPrefix.replace(/[+-]/g, '')
  const number = rawNumber.replace(/^[+-]\s*/, '')
  return <span className="formatted-money"><span>{prefix}</span><CurrencyMark currency={currency}/>{displayedSign&&<span className="formatted-money__sign">{displayedSign}</span>}<span>{number}</span></span>
}
