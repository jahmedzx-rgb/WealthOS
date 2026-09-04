function dateOnlyParts(value:string){
  const match=value.match(/^(\d{4})-(\d{2})-(\d{2})(?:$|T)/)
  return match?{year:match[1],month:match[2],day:match[3]}:null
}

const twoDigits=(value:number)=>String(value).padStart(2,'0')

export function formatWealthDate(value:string|Date){
  const date=value instanceof Date?value:new Date(value)
  if(Number.isNaN(date.getTime()))return''
  return`${twoDigits(date.getDate())}/${twoDigits(date.getMonth()+1)}/${date.getFullYear()}`
}

export function normalizeWealthDateInput(value:string){
  const digits=value.replace(/\D/g,'').slice(0,8)
  if(digits.length<=2)return digits
  if(digits.length<=4)return`${digits.slice(0,2)}/${digits.slice(2)}`
  return`${digits.slice(0,2)}/${digits.slice(2,4)}/${digits.slice(4)}`
}

export function parseWealthDate(value:string){
  const match=value.match(/^(\d{2})\/(\d{2})\/(\d{4})$/)
  if(!match)return null
  const day=Number(match[1]),month=Number(match[2]),year=Number(match[3])
  const date=new Date(year,month-1,day)
  return date.getFullYear()===year&&date.getMonth()===month-1&&date.getDate()===day?date:null
}

export function formatDayMonth(value:string|Date){
  const date=value instanceof Date?value:new Date(value)
  if(Number.isNaN(date.getTime()))return''
  return`${twoDigits(date.getDate())}/${twoDigits(date.getMonth()+1)}`
}

export function parseDayMonth(value:string){
  const match=value.match(/^(\d{2})\/(\d{2})$/)
  if(!match)return null
  const day=Number(match[1]),month=Number(match[2])
  if(month<1||month>12||day<1||day>new Date(2024,month,0).getDate())return null
  return{day,month}
}

export function formatDate(value:string|Date){
  if(typeof value==='string'){
    const parts=dateOnlyParts(value)
    if(parts&&!value.includes('T'))return new Intl.DateTimeFormat(displayLocale(),{day:'2-digit',month:'2-digit',year:'numeric',timeZone:'UTC'}).format(new Date(`${parts.year}-${parts.month}-${parts.day}T00:00:00Z`))
  }
  const date=value instanceof Date?value:new Date(value)
  if(Number.isNaN(date.getTime()))return'—'
  return new Intl.DateTimeFormat(displayLocale(),{day:'2-digit',month:'2-digit',year:'numeric'}).format(date)
}

export function formatDateTime(value:string|Date){
  const date=value instanceof Date?value:new Date(value)
  if(Number.isNaN(date.getTime()))return'—'
  return new Intl.DateTimeFormat(displayLocale(),{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit',hour12:false}).format(date)
}
import { displayLocale } from './localeFormat'
