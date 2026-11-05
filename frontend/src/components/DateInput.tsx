import { useEffect, useRef, useState, type ChangeEvent, type InputHTMLAttributes } from 'react'
import { useLanguage } from '../context/LanguageContext'

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'type' | 'value' | 'defaultValue'> & {
  type?: 'date' | 'datetime-local'; value?: string; defaultValue?: string; initialDraft?:string; onDraftChange?:(value:string)=>void
}

export function maskDateInput(value: string, withTime = false) {
  const digits = value.replace(/[^0-9٠-٩۰-۹]/g, '').slice(0, withTime ? 12 : 8)
  return digits.slice(0, 2) + (digits.length > 2 ? '/' + digits.slice(2, 4) : '')
    + (digits.length > 4 ? '/' + digits.slice(4, 8) : '')
    + (digits.length > 8 ? ' ' + digits.slice(8, 10) : '')
    + (digits.length > 10 ? ':' + digits.slice(10, 12) : '')
}

export function dateInputDisplay(value: string) {
  const match = value.match(/^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}:\d{2}))?/)
  return match ? `${match[3]}/${match[2]}/${match[1]}${match[4] ? ` ${match[4]}` : ''}` : ''
}

export function dateInputISO(value: string, withTime = false) {
  const normalized = value.replace(/[٠-٩۰-۹]/g, c => String(c.charCodeAt(0) - (c >= '۰' ? 1776 : 1632))).trim()
  const match = normalized.match(withTime ? /^(\d{2})\/(\d{2})\/(\d{4}) (\d{2}):(\d{2})$/ : /^(\d{2})\/(\d{2})\/(\d{4})$/)
  if (!match) return ''
  const [, day, month, year, hour = '00', minute = '00'] = match
  const date = new Date(`${year}-${month}-${day}T${hour}:${minute}:00`)
  if (Number(year) < 1 || Number(month) < 1 || Number(month) > 12 || Number(day) < 1 || Number(day) > new Date(Number(year), Number(month), 0).getDate() || Number(hour) > 23 || Number(minute) > 59 || Number.isNaN(date.getTime())) return ''
  return `${year}-${month}-${day}${withTime ? `T${hour}:${minute}` : ''}`
}

/** Fixed day/month/year presentation; API and FormData values remain ISO. */
export default function DateInput({ type = 'date', value, defaultValue = '', initialDraft, onDraftChange, onChange, name, min, max, ...props }: Props) {
  const { language } = useLanguage()
  const [draft, setDraft] = useState(() => initialDraft ?? dateInputDisplay(value ?? defaultValue))
  const emitted = useRef(value ?? defaultValue)
  const input = useRef<HTMLInputElement>(null)
  useEffect(() => {
    if (value !== undefined && value !== emitted.current) {
      emitted.current = value
      // Synchronize externally reset/loaded values, not each keystroke.

      setDraft(dateInputDisplay(value))
    }
  }, [value])
  const iso = dateInputISO(draft, type === 'datetime-local')
  useEffect(() => {
    const invalid = draft !== '' && (!iso || (typeof min === 'string' && iso < min) || (typeof max === 'string' && iso > max))
    input.current?.setCustomValidity(invalid ? (language === 'ar' ? 'أدخل تاريخًا صحيحًا بصيغة يوم/شهر/سنة ضمن النطاق المسموح.' : 'Enter a valid dd/mm/yyyy date within the allowed range.') : '')
  }, [draft, iso, min, max, language])
  return <>
    <input {...props} ref={input} type="text" dir="ltr" placeholder={type === 'datetime-local' ? 'dd/mm/yyyy hh:mm' : 'dd/mm/yyyy'} value={draft} onChange={event => {
      const text = maskDateInput(event.target.value, type === 'datetime-local')
      const next = dateInputISO(text, type === 'datetime-local')
      setDraft(text)
      onDraftChange?.(text)
      emitted.current = next
      onChange?.({ ...event, target: { ...event.target, value: next }, currentTarget: { ...event.currentTarget, value: next } } as ChangeEvent<HTMLInputElement>)
    }} />
    {name && <input type="hidden" name={name} value={iso} disabled={props.disabled} />}
  </>
}
