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
  let match=value.match(/^Portfolio opened\s*·\s*(.+)$/i)
  if(match)return`فتح محفظة · ${freeText(match[1])}`
  match=value.match(/^Bank account opened\s*·\s*(.+)$/i)
  if(match)return`فتح حساب بنكي · ${freeText(match[1])}`
  match=value.match(/^Credit card added\s*·\s*(.+)$/i)
  if(match)return`إضافة بطاقة ائتمانية · ${freeText(match[1])}`
  match=value.match(/^Deposit opened\s*·\s*(.+)$/i)
  if(match)return`فتح وديعة · ${systemName(match[1])}`
  match=value.match(/^Accounting reclassification\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`إعادة تصنيف محاسبي · ${freeText(match[1])} · ${systemName(match[2])}`
  match=value.match(/^(Buy|Sell)\s*·\s*(.+?)\s*·\s*([\d.,]+)\s+Units?$/i)
  if(match)return`${match[1].toLowerCase()==='buy'?'شراء':'بيع'} · ${systemName(match[2])} · ${match[3]} وحدة`
  match=value.match(/^Deposit funded\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`تمويل وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Opening deposit balance\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`رصيد وديعة افتتاحي · ${systemName(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Deposit broken\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`فك وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Deposit balance adjustment\s*·\s*([^·]+)\s*·\s*(.+)$/i)
  if(match)return`تسوية رصيد وديعة · ${freeText(match[1])} · ${freeText(match[2])}`
  match=value.match(/^Deposit income\s*·\s*(.+)$/i)
  if(match)return`دخل من وديعة · ${systemName(match[1])}`
  match=value.match(/^Deposit withdrawal\s*·\s*(.+)$/i)
  if(match)return`سحب من رصيد وديعة · ${systemName(match[1])}`
  match=value.match(/^Deposit principal returned\s*·\s*(.+)$/i)
  if(match)return`استرداد أصل وديعة · ${systemName(match[1])}`
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
  const dividendReceived=activity.description.match(/^(.+?)\s+distribution received\s*·\s*(.+)$/i)
  if(dividendReceived)return language==='ar'
    ? `استلام توزيعات أرباح · ${freeText(dividendReceived[1])} · ${freeText(dividendReceived[2])}`
    : `${dividendReceived[1].trim()} dividend received · ${dividendReceived[2].trim()}`
  if(activity.related_reference?.startsWith('credit-card-sadad:'))return language==='ar'?'سداد بين البطاقات':'Card-to-card payment'
  if(activity.related_reference?.startsWith('credit-card-adjustment:')){
    const adjustment=activity.description.match(/^(?:تسوية رصيد البطاقة الائتمانية|Credit card balance adjustment)\s*·\s*([^·]+)\s*·\s*(.+)$/i)
    if(adjustment)return language==='ar'
      ? `تسوية رصيد بطاقة ائتمانية · ${freeText(adjustment[1])} · ${freeText(adjustment[2])}`
      : `Credit card balance adjustment · ${adjustment[1].trim()} · ${adjustment[2].trim()}`
  }
  if(activity.related_reference?.startsWith('deposit-adjustment:')){
    const adjustment=activity.description.match(/^(?:تسوية رصيد الوديعة|تسوية رصيد وديعة|Deposit balance adjustment)\s*·\s*([^·]+)\s*·\s*(.+)$/i)
    if(adjustment)return language==='ar'
      ? `تسوية رصيد وديعة · ${freeText(adjustment[1])} · ${freeText(adjustment[2])}`
      : `Deposit balance adjustment · ${adjustment[1].trim()} · ${adjustment[2].trim()}`
  }
  if(/^opening-property(?:-valuation)?:/.test(activity.related_reference??'')){
    const property=activity.description.match(/^Opening property( valuation)?\s*·\s*(.+)$/i)
    if(property)return language==='ar'?`${property[1]?'تقييم عقار افتتاحي':'عقار افتتاحي'} · ${freeText(property[2])}`:activity.description
  }
  // Older opening entries store their system prefix in Arabic. Localize that
  // prefix only; never rewrite the account/card name or the persisted journal.
  if(/^(credit-card:|opening-credit-card:|opening-bank-account:)/.test(activity.related_reference??'')){
    const opening=activity.description.match(/^(?:رصيد افتتاحي|Opening balance)\s*·\s*(.+)$/i)
    if(opening)return language==='ar'?`رصيد افتتاحي · ${freeText(opening[1])}`:`Opening balance · ${opening[1]}`
  }
  if(/^private-loan(?:-payment)?:/.test(activity.related_reference??'')){
    const loan=activity.description.match(/^Private loan( payment)?:\s*(.+)$/i)
    if(loan)return language==='ar'?`${loan[1]?'سداد قرض خاص':'قرض خاص'}: ${freeText(loan[2])}`:activity.description
  }
  const normalized=/^Buy Security #\d+$/i.test(activity.description)?'Security Purchase':/^Sell Security #\d+$/i.test(activity.description)?'Security Sale':activity.description
  return language==='ar'?arabicActivityDescription({...activity,description:normalized}):normalized
}

export function activityDetail(activity:ActivityLike & {return_status?:'ACCRUED'|'REALIZED'|null},language:'en'|'ar'='en'){
  const reference=activity.related_reference
  let label='Posted Operation'
  const legacyCardOpening=reference?.startsWith('credit-card:')&&/^(?:Opening balance|رصيد افتتاحي)\s*·/i.test(activity.description)
  const legacyDepositOpening=reference?.startsWith('deposit:')&&/^Opening deposit balance\s*·/i.test(activity.description)
  if(reference?.startsWith('portfolio-created:'))label='Investment Channel Created'
  else if(reference?.startsWith('bank-account-created:'))label='Bank Account Created'
  else if(reference?.startsWith('credit-card-created:'))label='Credit Card Created'
  else if(reference?.startsWith('deposit-created:'))label='Deposit Channel Created'
  else if(reference?.startsWith('opening-')||legacyCardOpening||legacyDepositOpening)label='Opening Balance'
  else if(reference?.startsWith('portfolio-funding:'))label='Portfolio Funding'
  else if(reference?.startsWith('portfolio-withdrawal:'))label='Portfolio Withdrawal'
  else if(reference?.startsWith('property-sale:'))label='Property Sale'
  else if(reference?.startsWith('property-adjustment:'))label='Property Valuation Adjustment'
  else if(reference?.startsWith('property:'))label='Property'
  else if(reference?.startsWith('deposit-break:'))label='Deposit Closure'
  else if(reference?.startsWith('deposit-return:'))label=activity.return_status==='REALIZED'?'Deposit Income Realized':'Deposit Interest Credited'
  else if(reference?.startsWith('deposit-maturity:')&&reference.endsWith(':principal-return'))label='Deposit Principal Return'
  else if(reference?.startsWith('deposit-maturity:'))label='Deposit Income'
  else if(reference?.startsWith('deposit-adjustment:'))label='Deposit Balance Adjustment'
  else if(reference?.startsWith('deposit-withdrawal:'))label='Deposit Withdrawal'
  else if(reference?.startsWith('deposit:'))label='Deposit'
  else if(reference?.startsWith('credit-card-payment:'))label='Credit Card Payment'
  else if(reference?.startsWith('credit-card-sadad:'))label='Card-to-Card Transfer'
  else if(reference?.startsWith('credit-card-cashback:'))label='Cashback Income'
  else if(reference?.startsWith('credit-card-adjustment:'))label='Credit Card Balance Adjustment'
  else if(reference?.startsWith('credit-card:'))label='Credit Card'
  else if(reference?.startsWith('bank-account:'))label='Bank Account'
  else if(reference?.startsWith('security:'))label='Investment Trade'
  else if(reference?.startsWith('accounting-reclassification:'))label='Accounting Reclassification'
  if(language!=='ar')return label
  if(label==='Investment Channel Created')return'تم إنشاء قناة استثمارية'
  if(label==='Bank Account Created')return'تم إنشاء قناة بنكية'
  if(label==='Credit Card Created')return'تم إنشاء قناة ائتمانية'
  if(label==='Deposit Channel Created')return'تم إنشاء قناة ادخارية'
  const arabic:Record<string,string>={'Posted Operation':'عملية مُرحّلة','Cashback Income':'دخل الاسترداد النقدي','Portfolio Funding':'تمويل المحفظة','Portfolio Withdrawal':'سحب من المحفظة','Property Sale':'بيع عقار','Property Valuation Adjustment':'تعديل تقييم عقار','Property':'عقار','Deposit Closure':'إغلاق وديعة','Deposit Interest Credited':'عائد مضاف إلى رصيد الوديعة','Deposit Income Realized':'دخل وديعة محقق','Deposit Principal Return':'استرداد أصل وديعة','Deposit Income':'دخل من وديعة','Deposit Balance Adjustment':'تسوية رصيد وديعة','Deposit Withdrawal':'سحب من رصيد وديعة','Deposit':'وديعة','Credit Card Payment':'سداد بطاقة ائتمانية','Card-to-Card Transfer':'تحويل بين البطاقات','Credit Card Balance Adjustment':'تسوية رصيد بطاقة ائتمانية','Credit Card':'بطاقة ائتمانية','Bank Account':'حساب بنكي','Investment Trade':'عملية استثمارية','Opening Balance':'رصيد افتتاحي','Accounting Reclassification':'إعادة تصنيف محاسبي'}
  return arabic[label]??label
}
