export function parseAmountInput(value: string) {
  const normalized = value.replace(/[٠-٩۰-۹]/g, c => String(c.charCodeAt(0) - (c >= '۰' ? 1776 : 1632)))
    .replace(/٫/g, '.').replace(/[,٬\s]/g, '')
  return normalized
}

export function displayAmountInput(value: string, language = 'en') {
  if (!/^-?\d*(\.\d*)?$/.test(value)) return value
  const negative = value.startsWith('-')
  const [whole, fraction] = (negative ? value.slice(1) : value).split('.')
  const grouped = (negative ? '-' : '') + whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',') + (fraction !== undefined ? '.' + fraction : '')
  return language === 'ar' ? grouped.replace(/\d/g, d => '٠١٢٣٤٥٦٧٨٩'[Number(d)]).replace(/,/g, '٬').replace(/\./g, '٫') : grouped
}
