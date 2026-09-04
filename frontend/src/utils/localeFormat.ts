import type { Language } from '../context/LanguageContext'

export const displayLocale = (language?: Language) => {
  const resolved = language ?? (typeof document !== 'undefined' && document.documentElement.lang === 'ar' ? 'ar' : 'en')
  return resolved === 'ar' ? 'ar-SA-u-nu-arab' : 'en-US-u-nu-latn'
}

export function formatDisplayNumber(value: number, options?: Intl.NumberFormatOptions, language?: Language) {
  return new Intl.NumberFormat(displayLocale(language), options).format(value)
}

export function formatDisplayPercent(value: number, fractionDigits = 1, language?: Language) {
  return new Intl.NumberFormat(displayLocale(language), {
    style: 'percent',
    minimumFractionDigits: fractionDigits,
    maximumFractionDigits: fractionDigits,
  }).format(value / 100)
}

export function formatDisplayInteger(value: number, language?: Language) {
  return formatDisplayNumber(value, { maximumFractionDigits: 0 }, language)
}
