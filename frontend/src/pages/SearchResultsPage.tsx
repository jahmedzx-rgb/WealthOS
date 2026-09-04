/* eslint-disable react-hooks/set-state-in-effect */
import { ArrowUpRight, BookOpen, BriefcaseBusiness, Building2, CreditCard, FileClock, Landmark, LibraryBig, ListTree, Search, Settings, Sprout, WalletCards } from 'lucide-react'
import { useEffect, useMemo, useState, type ElementType, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { operationRegistry } from '../operations/operationRegistry'
import { getFinancialSummary, getJournalEntries } from '../services/accountingService'
import { formatDate } from '../utils/dateFormat'
import { getBrokers } from '../services/brokerService'
import { getPortfolioSummary } from '../services/portfolioService'
import './SearchResultsPage.css'
import { addRecentSearch } from '../utils/searchHistory'
import { useLanguage } from '../context/LanguageContext'

type SearchItem={id:string;title:string;description:string;category:string;route:string;keywords:string;icon:ElementType}

const destinations:SearchItem[]=[
  {id:'page-investing',title:'Investing',description:'Investments, deposits, allocation, and market positions.',category:'Page',route:'/investing',keywords:'investing investment استثمار استثمارات وديعة ودائع',icon:BriefcaseBusiness},
  {id:'page-positions',title:'Investment Positions',description:'Review listed securities and investment positions.',category:'Page',route:'/investing/positions',keywords:'stock fund security position سهم صندوق مركز استثماري',icon:BriefcaseBusiness},
  {id:'page-cash',title:'Cash',description:'Cash on hand, bank balances, and brokerage cash.',category:'Page',route:'/investing/cash',keywords:'cash liquidity bank brokerage نقد كاش سيولة حساب',icon:WalletCards},
  {id:'page-banks',title:'Bank Accounts',description:'Balances, cash inflows, and cash outflows.',category:'Page',route:'/bank-accounts',keywords:'bank cash account بنك حساب كاش',icon:Landmark},
  {id:'page-cards',title:'Credit Cards',description:'Credit limits, used balances, and payments.',category:'Page',route:'/credit-cards',keywords:'credit card liability بطاقة ائتمانية دين',icon:CreditCard},
  {id:'page-accounting',title:'Accounting',description:'Balance sheet, income statement, cash flow, and liabilities.',category:'Page',route:'/accounting',keywords:'accounting balance sheet income cash flow محاسبة ميزانية دخل تدفق',icon:BookOpen},
  {id:'page-ledger',title:'General Ledger',description:'Every posted debit and credit.',category:'Page',route:'/accounting/ledger',keywords:'ledger debit credit دفتر استاذ مدين دائن',icon:BookOpen},
  {id:'page-journals',title:'Journal Entries',description:'Balanced entries created by posted operations.',category:'Page',route:'/accounting/journals',keywords:'journal entry قيد قيود يومية',icon:BookOpen},
  {id:'page-reporting',title:'Reporting',description:'Live financial reports generated from posted entries.',category:'Page',route:'/reporting',keywords:'report statement تقرير تقارير قوائم',icon:FileClock},
  {id:'page-library',title:'Library',description:'Documents analyzed by WealthOS and their extracted operations.',category:'Page',route:'/library',keywords:'library document file upload import مكتبة مستند ملف رفع استيراد',icon:LibraryBig},
  {id:'page-index',title:'Index',description:'Every WealthOS page and financial operation in one place.',category:'Page',route:'/index',keywords:'index directory navigation links pages operations فهرس دليل روابط صفحات عمليات',icon:ListTree},
  {id:'page-settings',title:'Settings',description:'Profile, currencies, security, backup, and account controls.',category:'Page',route:'/settings',keywords:'settings currency profile security إعدادات عملة ملف أمان',icon:Settings},
]

const normalize=(value:string)=>value.trim().toLocaleLowerCase().replaceAll(',','').replaceAll('٬','').replace(/\s+/g,' ')
const amountLabel=(value:number,currency='SAR')=>`${new Intl.NumberFormat('en-US',{minimumFractionDigits:2,maximumFractionDigits:2}).format(value)} ${currency}`
const amountKeywords=(...values:number[])=>values.map(value=>`${value} ${new Intl.NumberFormat('en-US',{maximumFractionDigits:2}).format(value)}`).join(' ')

export default function SearchResultsPage(){
  const{t}=useLanguage()
  const[params,setParams]=useSearchParams();const query=params.get('q')??'';const[input,setInput]=useState(query);const[liveItems,setLiveItems]=useState<SearchItem[]>([]);const[loading,setLoading]=useState(true)
  useEffect(()=>setInput(query),[query])
  useEffect(()=>{if(query.trim())addRecentSearch(query)},[query])
  useEffect(()=>{let active=true;Promise.allSettled([getFinancialSummary(),getPortfolioSummary('consolidated'),getBrokers(),getJournalEntries()]).then(([financialResult,portfolioResult,brokersResult,journalsResult])=>{if(!active)return;const items:SearchItem[]=[]
    if(financialResult.status==='fulfilled'){
      const data=financialResult.value
      items.push(
        ...data.bank_accounts.map(item=>({id:`bank-${item.id}`,title:item.account_name||item.bank_name,description:`${item.bank_name} · Balance ${amountLabel(item.current_balance,item.currency_code)}`,category:'Bank Account',route:'/bank-accounts',keywords:`${item.account_name} ${item.bank_name} ${item.account_type} ${amountKeywords(item.current_balance)} bank account balance بنك حساب رصيد`,icon:Landmark})),
        ...data.credit_cards.map(item=>({id:`card-${item.id}`,title:`${item.card_name} •• ${item.last4}`,description:`${item.issuer_bank} · Used ${amountLabel(item.current_balance,item.currency_code)} · Limit ${amountLabel(item.credit_limit,item.currency_code)}`,category:'Credit Card',route:'/credit-cards',keywords:`${item.card_name} ${item.issuer_bank} ${item.last4} ${amountKeywords(item.current_balance,item.credit_limit,item.credit_limit-item.current_balance,item.minimum_monthly_payment)} credit card used limit remaining بطاقة ائتمانية مستخدم حد متبقي`,icon:CreditCard})),
        ...data.deposits.map(item=>({id:`deposit-${item.id}`,title:item.product_name,description:`${item.provider_name} · ${amountLabel(item.current_balance,item.currency_code)} · ${item.annual_return_rate}%`,category:'Deposit',route:`/operations/deposit?edit=${item.id}`,keywords:`${item.product_name} ${item.provider_name} ${amountKeywords(item.current_balance,item.principal_amount,item.annual_return_rate)} deposit savings return balance وديعة ادخار عائد رصيد`,icon:Sprout})),
        ...data.recent_activity.map(item=>({id:`activity-${item.id}`,title:item.description,description:`${amountLabel(item.cash_change)} · Posted ${formatDate(item.transaction_date)}`,category:'Activity',route:'/activity',keywords:`${item.description} ${item.related_reference??''} ${amountKeywords(item.cash_change,Math.abs(item.cash_change))} transaction operation amount عملية حركة مبلغ`,icon:FileClock})),
        ...data.asset_breakdown.map(item=>({id:`asset-${item.code}`,title:`${item.code} · ${item.name}`,description:`Posted asset balance · ${amountLabel(item.balance)}`,category:'Ledger Account',route:'/accounting/ledger',keywords:`${item.code} ${item.name} ${amountKeywords(item.balance)} asset balance أصل رصيد`,icon:WalletCards})),
        ...data.liability_breakdown.map(item=>({id:`liability-${item.code}`,title:`${item.code} · ${item.name}`,description:`Posted liability balance · ${amountLabel(item.balance)}`,category:'Ledger Account',route:'/accounting/ledger',keywords:`${item.code} ${item.name} ${amountKeywords(item.balance)} liability balance التزام دين رصيد`,icon:WalletCards})),
      )
    }
    if(portfolioResult.status==='fulfilled')items.push(...portfolioResult.value.positions.map(item=>({id:`security-${item.security_id}`,title:`${item.symbol} · ${item.name}`,description:`${item.security_type.replaceAll('_',' ')} · Market value ${amountLabel(item.market_value,item.currency_code)}`,category:'Investment',route:'/investing/positions',keywords:`${item.symbol} ${item.name} ${item.security_type} ${item.exchange} ${amountKeywords(item.quantity,item.average_cost,item.total_cost,item.market_price,item.market_value,item.unrealized_pl)} stock fund security value price cost return سهم صندوق قيمة سعر تكلفة عائد`,icon:BriefcaseBusiness})))
    if(brokersResult.status==='fulfilled')items.push(...brokersResult.value.map(item=>({id:`broker-${item.id}`,title:item.name,description:[item.country,item.website].filter(Boolean).join(' · ')||'Registered broker',category:'Broker',route:'/investing/brokers',keywords:`${item.name} ${item.code} ${item.country??''} broker وسيط`,icon:Building2})))
    if(journalsResult.status==='fulfilled')items.push(...journalsResult.value.map(item=>{const debit=item.lines.reduce((sum,line)=>sum+line.debit,0);const lineAmounts=item.lines.flatMap(line=>[line.debit,line.credit]).filter(value=>value!==0);return{id:`journal-${item.id}`,title:item.description,description:`JE-${String(item.id).padStart(4,'0')} · ${amountLabel(debit)} · ${formatDate(item.transaction_date)}`,category:'Journal Entry',route:'/accounting/journals',keywords:`${item.description} ${item.related_reference??''} ${item.lines.map(line=>`${line.account_code} ${line.account_name}`).join(' ')} ${amountKeywords(debit,...lineAmounts)} JE-${item.id} journal entry debit credit قيد مدين دائن`,icon:BookOpen}}))
    setLiveItems(items);setLoading(false)});return()=>{active=false}},[])
  const operationItems=Object.values(operationRegistry).filter(item=>item.status==='active').map<SearchItem>(item=>({id:`operation-${item.id}`,title:item.title,description:item.description,category:'Operation',route:item.route,keywords:`${item.title} ${item.description} operation عملية`,icon:item.icon}))
  const results=useMemo(()=>{const needle=normalize(query);if(!needle)return[];return [...destinations,...operationItems,...liveItems].filter(item=>normalize(`${item.title} ${item.description} ${item.category} ${item.keywords}`).includes(needle)).filter((item,index,array)=>array.findIndex(candidate=>candidate.id===item.id)===index)},[query,liveItems,operationItems])
  function submit(event:FormEvent){event.preventDefault();const value=input.trim();if(value)setParams({q:value})}
  return <section className="search-results-page"><PageHeader title={t('Search')} subtitle={t('Search your real WealthOS records, operations, and destinations.')} icon={Search}/><form className="search-results-page__form" onSubmit={submit}><Search size={18}/><input autoFocus value={input} onChange={event=>setInput(event.target.value)} placeholder={t('Search accounts, cards, deposits, investments, operations…')}/><button type="submit" disabled={!input.trim()}>{t('Search')}</button></form><div className="search-results-page__summary"><div><h2>{query?`${t('Results For')} “${query}”`:t('Search WealthOS')}</h2><p>{loading?t('Loading your records…'):query?`${results.length} ${t(results.length===1?'matching result':'matching results')}`:t('Enter a word or name to begin.')}</p></div></div>{!loading&&query&&results.length>0?<div className="search-results-page__list">{results.map(item=>{const Icon=item.icon;return <Link to={item.route} key={item.id}><span><Icon size={18}/></span><div><small>{t(item.category)}</small><strong>{t(item.title)}</strong><p>{t(item.description)}</p></div><em>{t('Open')} <ArrowUpRight size={14}/></em></Link>})}</div>:null}{!loading&&query&&!results.length?<div className="search-results-page__empty"><Search size={25}/><strong>{t('No Matching Results')}</strong><p>{t('Try the name of an account, card, deposit, broker, investment, operation, or page.')}</p></div>:null}</section>
}
