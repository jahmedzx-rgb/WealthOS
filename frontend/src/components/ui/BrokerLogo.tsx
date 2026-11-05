import { Building2 } from 'lucide-react'
import './BrokerLogo.css'

function brokerKey(name:string){
  const value=name.trim().toLowerCase()
  if(value.includes('afaq')||value.includes('آفاق')||value.includes('افاق'))return 'afaq'
  if((value.includes('abyan')||value.includes('أبيان')||value.includes('ابيان'))&&(value.includes('trading')||value.includes('trade')||value.includes('تداول')))return 'abyan-trading'
  if((value.includes('abyan')||value.includes('أبيان')||value.includes('ابيان'))&&(value.includes('capital')||value.includes('كابيتال')||value.includes('المالية')))return 'abyan-capital'
  if((value.includes('alkhabeer')||value.includes('al khabeer')||value.includes('الخبير'))&&(value.includes('global')||value.includes('قلوبال')||value.includes('جلوبال')||value.includes('العالمي')))return 'alkhabeer-global'
  if(value.includes('alkhabeer')||value.includes('al khabeer')||value.includes('الخبير'))return 'alkhabeer-capital'
  if(value.includes('alinma')||value.includes('الإنماء')||value.includes('الانماء'))return 'alinma-capital'
  if(value.includes('snb')||value.includes('alahli')||value.includes('al ahli')||value.includes('الأهلي')||value.includes('الاهلي'))return 'snb-capital'
  if(value.includes('rajhi')||value.includes('الراجحي'))return 'rajhi-capital'
  return ''
}

function brokerBrand(name:string){
  const value=name.trim().toLowerCase()
  if(value.includes('afaq')||value.includes('آفاق')||value.includes('افاق'))return 'afaq'
  if((value.includes('abyan')||value.includes('أبيان')||value.includes('ابيان'))&&(value.includes('trading')||value.includes('trade')||value.includes('تداول')))return 'abyan-trading'
  if((value.includes('abyan')||value.includes('أبيان')||value.includes('ابيان'))&&(value.includes('capital')||value.includes('كابيتال')||value.includes('المالية')))return 'abyan-capital'
  if(value.includes('alkhabeer')||value.includes('al khabeer')||value.includes('الخبير'))return 'alkhabeer'
  if(value.includes('alinma')||value.includes('الإنماء')||value.includes('الانماء'))return 'alinma'
  if(value.includes('snb')||value.includes('alahli')||value.includes('al ahli')||value.includes('الأهلي')||value.includes('الاهلي'))return 'snb'
  if(value.includes('abyan')||value.includes('أبيان')||value.includes('ابيان'))return 'abyan'
  if(value.includes('riyad')||value.includes('الرياض'))return 'riyad'
  if(value.includes('rajhi')||value.includes('الراجحي'))return 'rajhi'
  if(value.includes('derayah')||value.includes('دراية')||value.includes('درايه'))return 'derayah'
  if(value.includes('sahm')||value.includes('سهم'))return 'sahm'
  if(value.includes('bilad')||value.includes('البلاد'))return 'bilad'
  if(value.includes('hsbc'))return 'hsbc'
  if(value.includes('interactive brokers')||value.includes('ibkr'))return 'ibkr'
  if(value.includes('webull'))return 'webull'
  if(value.includes('jazira')||value.includes('الجزيرة'))return 'aljazira'
  if(value.includes('anb')||value.includes('arab national')||value.includes('العربي'))return 'anb'
  if(value.includes('sab invest')||value.includes('sabb invest')||value.includes('ساب للاستثمار'))return 'sab'
  if(value.includes('bsf')||value.includes('fransi')||value.includes('الفرنسي'))return 'bsf'
  if(value.includes('alistithmar')||value.includes('الاستثمار كابيتال'))return 'alistithmar'
  if(value.includes('jadwa')||value.includes('جدوى'))return 'jadwa'
  if(value.includes('gib capital')||value.includes('جي آي بي'))return 'gib'
  if(value.includes('yaqeen')||value.includes('falcom')||value.includes('يقين'))return 'yaqeen'
  if(value.includes('awaed')||value.includes('عوائد'))return 'awaed'
  if(value.includes('fidelity'))return 'fidelity'
  if(value.includes('schwab'))return 'schwab'
  if(value.includes('etrade')||value.includes('e*trade'))return 'etrade'
  if(value.includes('robinhood'))return 'robinhood'
  if(value.includes('vanguard'))return 'vanguard'
  if(value.includes('merrill'))return 'merrill'
  if(value.includes('tradestation'))return 'tradestation'
  if(value.includes('tastytrade')||value.includes('tastyworks'))return 'tastytrade'
  if(value.includes('sofi'))return 'sofi'
  if(value==='public'||value.includes('public.com'))return 'public'
  if(value.includes('moomoo'))return 'moomoo'
  return 'default'
}

export default function BrokerLogo({name}:{name:string}){
  const key=brokerKey(name)
  const brand=brokerBrand(name)
  const logoFile=key==='afaq'?'afaq.ico':key==='abyan-trading'?'abyan-trading.png':key==='abyan-capital'?'abyan.png':key?`${key}.png`:''
  return <span className={`broker-logo brand-${brand}${key?` is-${key}`:''}`} aria-hidden="true">
    {key?<img src={`/brokers/${logoFile}?v=local-20261029`} alt="" width={34} height={34} loading="eager" decoding="async"/>:<Building2 size={17}/>}
  </span>
}
