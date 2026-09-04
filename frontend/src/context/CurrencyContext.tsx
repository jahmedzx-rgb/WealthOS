/* eslint-disable react-refresh/only-export-components */
import { createContext, useContext, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { useLanguage } from './LanguageContext'
import { displayLocale } from '../utils/localeFormat'

export const supportedCurrencies = [
  { code: 'SAR', name: 'Saudi Riyal', symbol: '\u20C1', sarRate: 1 },
  { code: 'USD', name: 'US Dollar', symbol: '$', sarRate: 3.75 },
  { code: 'EUR', name: 'Euro', symbol: '€', sarRate: 4.08 },
  { code: 'GBP', name: 'British Pound', symbol: '£', sarRate: 4.76 },
  { code: 'JPY', name: 'Japanese Yen', symbol: '¥', sarRate: .025 },
  { code: 'AED', name: 'UAE Dirham', symbol: 'د.إ', sarRate: 1.021 },
  { code: 'KWD', name: 'Kuwaiti Dinar', symbol: 'د.ك', sarRate: 12.22 },
] as const

export type Currency = typeof supportedCurrencies[number]['code']
type Value = { currency: Currency; baseCurrency: Currency; enabledCurrencies: Currency[]; selectCurrency: (currency: Currency) => void; setBaseCurrency: (currency: Currency) => void; toggleEnabledCurrency: (currency: Currency) => void; formatMoney: (value: number, source?: Currency, compact?: boolean) => string }
const Context = createContext<Value | null>(null)

const initialEnabled = (): Currency[] => {
  try {
    const value = JSON.parse(localStorage.getItem('wealthos-enabled-currencies') || '[]')
    return value.length ? value as Currency[] : ['SAR', 'USD']
  } catch {
    return ['SAR', 'USD']
  }
}

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const { language } = useLanguage()
  const [currency, setCurrency] = useState<Currency>(() => (localStorage.getItem('wealthos-currency') as Currency) || 'SAR')
  const [baseCurrency, setBase] = useState<Currency>(() => (localStorage.getItem('wealthos-base-currency') as Currency) || 'SAR')
  const [enabledCurrencies, setEnabled] = useState<Currency[]>(initialEnabled)

  const selectCurrency = (next: Currency) => {
    setCurrency(next)
    localStorage.setItem('wealthos-currency', next)
  }

  const value = useMemo<Value>(() => ({
    currency,
    baseCurrency,
    enabledCurrencies,
    selectCurrency,
    setBaseCurrency: (next) => {
      setBase(next)
      selectCurrency(next)
      localStorage.setItem('wealthos-base-currency', next)
      if (!enabledCurrencies.includes(next)) {
        const updated = [...enabledCurrencies, next]
        setEnabled(updated)
        localStorage.setItem('wealthos-enabled-currencies', JSON.stringify(updated))
      }
    },
    toggleEnabledCurrency: (next) => setEnabled((current) => {
      if (next === baseCurrency) return current
      const updated = current.includes(next) ? current.filter((item) => item !== next) : [...current, next]
      if (!updated.includes(currency)) selectCurrency(baseCurrency)
      localStorage.setItem('wealthos-enabled-currencies', JSON.stringify(updated))
      return updated
    }),
    formatMoney: (amount, source = 'SAR', compact = false) => {
      const from = supportedCurrencies.find((item) => item.code === source)?.sarRate || 1
      const to = supportedCurrencies.find((item) => item.code === currency)?.sarRate || 1
      const converted = amount * from / to
      if (currency === 'SAR') {
        const formatted = new Intl.NumberFormat(displayLocale(language), { notation: compact ? 'compact' : 'standard', maximumFractionDigits: compact ? 1 : 2, minimumFractionDigits: compact ? 0 : 2 }).format(converted)
        return `\u20C1 ${formatted}`
      }
      return new Intl.NumberFormat(displayLocale(language), { style: 'currency', currency, notation: compact ? 'compact' : 'standard', maximumFractionDigits: compact ? 1 : currency === 'JPY' ? 0 : 2 }).format(converted)
    },
  }), [currency, baseCurrency, enabledCurrencies, language])

  return <Context.Provider value={value}>{children}</Context.Provider>
}

export function useCurrency() {
  const value = useContext(Context)
  if (!value) throw new Error('CurrencyProvider is missing')
  return value
}
