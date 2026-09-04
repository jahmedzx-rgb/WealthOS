import { supportedCurrencies, type Currency } from '../../context/CurrencyContext'
import './CurrencyMark.css'

type Props = { currency: Currency; className?: string }

export default function CurrencyMark({ currency, className = '' }: Props) {
  const item = supportedCurrencies.find((candidate) => candidate.code === currency)
  const symbol = currency === 'SAR' ? '\u20C1' : item?.symbol ?? currency
  return <span className={`currency-mark currency-mark--${currency.toLowerCase()} ${className}`.trim()} aria-hidden="true">{symbol}</span>
}
