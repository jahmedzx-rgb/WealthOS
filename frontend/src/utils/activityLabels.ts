type ActivityLike = { description:string;related_reference:string|null }

const systemNames:Record<string,string>={
  'Alkhabeer REIT Fund':'صندوق الخبير ريت',
  'Alkhabeer REIT':'صندوق الخبير ريت',
  'Wadaie':'ودائع',
  'Monthly Deposit':'وديعة شهرية',
}

// Isolates preserve the visual order of user-entered Latin text inside Arabic UI.
function freeText(value:string){return`\u2068${value.trim()}\u2069`}
function systemName(value:string){const clean=value.trim();return systemNames[clean]??freeText(clean)}

function arabicActivityDescription(activity:ActivityLike){
  const value=activity.description.trim()
  let match=value.match(/^Accounting reclassification\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`إعادة تصنيف محاسبي · ${freeText(match[1])} · ${systemName(match[2])}`
  match=value.match(/^(Buy|Sell)\s*·\s*(.+?)\s*·\s*([\d.,]+)\s+Units?$/i)
  if(match)return`${match[1].toLowerCase()==='buy'?'شراء':'بيع'} · ${systemName(match[2])} · ${match[3]} وحدة`
  match=value.match(/^Deposit funded\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`تمويل وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Deposit broken\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`فك وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Deposit balance adjustment\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`تسوية رصيد وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Property Purchase:\s*(.+?)(?:\s*·\s*Transfer Tax\s*(.+))?$/i)
  if(match)return`شراء عقار: ${freeText(match[1])}${match[2]?` · ضريبة التصرفات العقارية ${freeText(match[2])}`:''}`
  match=value.match(/^Opening balance\s*·\s*(.+)$/i)
  if(match)return`رصيد افتتاحي · ${freeText(match[1])}`
  const exact:Record<string,string>={
    'Cash Deposit':'إيداع نقدي','Credit Card Payment':'سداد بطاقة ائتمانية',
    'Security Purchase':'شراء ورقة مالية','Security Sale':'بيع ورقة مالية',
  }
  return exact[value]??value
}

export function activityTitle(activity:ActivityLike,language:'en'|'ar'='en'){
  const normalized=/^Buy Security #\d+$/i.test(activity.description)?'Security Purchase':/^Sell Security #\d+$/i.test(activity.description)?'Security Sale':activity.description
  return language==='ar'?arabicActivityDescription({...activity,description:normalized}):normalized
}

export function activityDetail(activity:ActivityLike,language:'en'|'ar'='en'){
  const reference=activity.related_reference
  let label='Posted Operation'
  if(reference?.startsWith('portfolio-funding:'))label='Portfolio Funding'
  else if(reference?.startsWith('portfolio-withdrawal:'))label='Portfolio Withdrawal'
  else if(reference?.startsWith('property-sale:'))label='Property Sale'
  else if(reference?.startsWith('property-adjustment:'))label='Property Valuation Adjustment'
  else if(reference?.startsWith('property:'))label='Property'
  else if(reference?.startsWith('deposit-break:'))label='Deposit Closure'
  else if(reference?.startsWith('deposit-adjustment:'))label='Deposit Balance Adjustment'
  else if(reference?.startsWith('deposit:'))label='Deposit'
  else if(reference?.startsWith('credit-card-payment:'))label='Credit Card Payment'
  else if(reference?.startsWith('credit-card-adjustment:'))label='Credit Card Balance Adjustment'
  else if(reference?.startsWith('credit-card:'))label='Credit Card'
  else if(reference?.startsWith('bank-account:'))label='Bank Account'
  else if(reference?.startsWith('security:'))label='Investment Trade'
  else if(reference?.startsWith('opening-'))label='Opening Balance'
  else if(reference?.startsWith('accounting-reclassification:'))label='Accounting Reclassification'
  if(language!=='ar')return label
  const arabic:Record<string,string>={'Posted Operation':'عملية مُرحّلة','Portfolio Funding':'تمويل المحفظة','Portfolio Withdrawal':'سحب من المحفظة','Property Sale':'بيع عقار','Property Valuation Adjustment':'تعديل تقييم عقار','Property':'عقار','Deposit Closure':'إغلاق وديعة','Deposit Balance Adjustment':'تسوية رصيد وديعة','Deposit':'وديعة','Credit Card Payment':'سداد بطاقة ائتمانية','Credit Card Balance Adjustment':'تسوية رصيد بطاقة ائتمانية','Credit Card':'بطاقة ائتمانية','Bank Account':'حساب بنكي','Investment Trade':'عملية استثمارية','Opening Balance':'رصيد افتتاحي','Accounting Reclassification':'إعادة تصنيف محاسبي'}
  return arabic[label]??label
}
