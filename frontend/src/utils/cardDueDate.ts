export function cardDayMonth(date: string | null | undefined, savedDay: number | null, now = new Date()): string {
  const parts = date?.match(/^\d{4}-(\d{2})-(\d{2})$/)
  if (parts) return `${parts[2]}/${parts[1]}`
  return `${savedDay ? String(savedDay).padStart(2, '0') : ''}/${String(now.getMonth() + 1).padStart(2, '0')}`
}

export function cardDateThisYear(value: string, now = new Date()): string | null {
  const parts = value.match(/^(\d{1,2})\/(\d{1,2})$/)
  if (!parts) return null
  const iso = `${now.getFullYear()}-${parts[2].padStart(2, '0')}-${parts[1].padStart(2, '0')}`
  return cardDaysUntil(iso, now) === null ? null : iso
}

export function cardDaysUntil(date: string | null | undefined, now = new Date(), savedDay?: number | null): number | null {
  // Legacy cards retain only a billing day. Use this month, never silently
  // move an unpaid deadline into the next month. Exact dates take precedence.
  if (!date && savedDay && Number.isInteger(savedDay) && savedDay >= 1 && savedDay <= 31) {
    const day = Math.min(savedDay, new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate())
    return day - now.getDate()
  }
  const match = date?.match(/^(\d{4})-(\d{2})-(\d{2})$/)
  if (!match) return null
  const year = Number(match[1]), month = Number(match[2]), day = Number(match[3])
  const due = new Date(Date.UTC(year, month - 1, day))
  if (due.getUTCFullYear() !== year || due.getUTCMonth() !== month - 1 || due.getUTCDate() !== day) return null
  return Math.round((due.getTime() - Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())) / 86400000)
}
