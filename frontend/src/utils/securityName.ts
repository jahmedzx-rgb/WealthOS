type LocalizedSecurity={symbol?:string;name:string;name_ar?:string|null;name_en?:string|null}

const officialEnglishNames:Record<string,string>={
  '3030':'Saudi Cement Company',
  '4002':'Mouwasat Medical Services Company',
  '4348':'Alkhabeer REIT Fund',
  '4703':'SEDCO Capital Multi Asset Traded Fund',
  '7010':'Saudi Telecom Company (stc)',
  '9403':'Albilad Saudi Sovereign Sukuk ETF',
  '2083':'Power and Water Utility Company for Jubail and Yanbu (Marafiq)',
  '4336':'Mulkia Gulf Real Estate REIT Fund',
  '4700':'Alkhabeer Diversified Income Traded Fund',
}

const compactEnglishNames:Record<string,string>={
  '3030':'Saudi Cement',
  '4002':'Mouwasat',
  '4348':'Alkhabeer REIT',
  '4703':'SEDCO',
  '7010':'STC',
  '9403':'Albilad',
  '2083':'Marafiq',
  '4336':'Mulkia REIT',
  '4700':'Alkhabeer Income',
}

const displaySymbols:Record<string,string>={
  'RJ-MONTHLY':'Rajhi ETF',
  'RJ-MONTHLY-II':'Rajhi ETF II',
}

export function securityDisplaySymbol(symbol:string){
  return displaySymbols[symbol]??symbol
}

export function securityDisplayName(security:LocalizedSecurity,language:'en'|'ar'){
  return language==='ar'?(security.name_ar||security.name):(security.symbol&&officialEnglishNames[security.symbol]||security.name_en||security.name)
}

export function securityCompactName(security:LocalizedSecurity,language:'en'|'ar'){
  if(language==='ar')return security.name_ar||security.name
  return security.symbol&&compactEnglishNames[security.symbol]||security.name_en||security.name
}
