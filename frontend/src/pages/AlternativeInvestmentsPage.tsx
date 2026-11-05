import DateInput from '../components/DateInput'
import { Building2, ChevronDown, Landmark, Plus, TrendingUp, X, Zap } from 'lucide-react'
import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import BrokerLogo from '../components/ui/BrokerLogo'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { createAlternativeInvestment, getAlternativeInvestments, type AlternativeInvestment } from '../services/accountingService'
import { getFinancialPlatforms, type FinancialPlatform } from '../services/financialPlatformService'
import { formatDate } from '../utils/dateFormat'
import { formatDisplayInteger, formatDisplayPercent } from '../utils/localeFormat'
import './InvestmentProductPages.css'

const nowInput=()=>{const d=new Date();d.setMinutes(d.getMinutes()-d.getTimezoneOffset());return d.toISOString().slice(0,16)}
const today=()=>nowInput().slice(0,10)
const typeLabel=(value:string)=>value==='VENTURE_CAPITAL'?'Angel Investment':value.replaceAll('_',' ').toLowerCase().replace(/\b\w/g,c=>c.toUpperCase())

const categories=[
  {type:'MANAGED_PORTFOLIO',title:'Managed Portfolio',description:'A managed portfolio containing shares, funds, or other securities.',icon:TrendingUp},
  {type:'DEBT_CROWDFUNDING',title:'Debt Financing',description:'Project-financing funds, private debt, sukuk, or peer-to-peer lending.',icon:Landmark},
  {type:'REAL_ESTATE_CROWDFUNDING',title:'Real Estate Participation',description:'A fractional property or real-estate development participation.',icon:Building2},
  {type:'PRIVATE_EQUITY',title:'Private Equity',description:'Ownership in private companies, including angel investments.',icon:Zap},
] as const

const familyOf=(type:string)=>!type?'':type==='MANAGED_PORTFOLIO'?'MANAGED_PORTFOLIO':type==='REAL_ESTATE_CROWDFUNDING'?'REAL_ESTATE_CROWDFUNDING':['VENTURE_CAPITAL','PRIVATE_EQUITY','EQUITY_CROWDFUNDING'].includes(type)?'PRIVATE_EQUITY':'DEBT_CROWDFUNDING'
const platformSupports=(platform:FinancialPlatform,type:string)=>{
  const services=new Set(platform.services)
  if(type==='MANAGED_PORTFOLIO')return services.has('MANAGED_PORTFOLIO')||services.has('ROBO_ADVISOR')
  if(type==='DEBT_CROWDFUNDING')return services.has('DEBT_CROWDFUNDING')
  if(type==='PRIVATE_FUND')return services.has('PRIVATE_FUND')
  if(type==='PRIVATE_SUKUK')return services.has('PRIVATE_SUKUK')
  if(type==='P2P_LENDING')return services.has('P2P_LENDING')
  if(type==='REAL_ESTATE_CROWDFUNDING')return services.has('REAL_ESTATE_CROWDFUNDING')||services.has('REAL_ESTATE_FUNDS')
  if(type==='PRIVATE_EQUITY'||type==='VENTURE_CAPITAL')return services.has('EQUITY_CROWDFUNDING')||services.has('PRIVATE_EQUITY')||services.has('VENTURE_CAPITAL')
  return false
}

const managedPortfolioMetrics=(item:AlternativeInvestment)=>{
  const notes=item.notes??''
  const activeCycle=notes.split('2026:')[1]?.split('. NAV')[0]??''
  const reinvested=[...activeCycle.matchAll(/D(\d+(?:\.\d+)?)/g)].reduce((sum,match)=>sum+Number(match[1]),0)
  const invested=Number(item.principal_amount)
  const marketValue=Number(item.current_value)
  const currentCycleReturn=marketValue-invested
  const previous=notes.split('2026:')[0]??''
  const previousTransactions=previous.split('8/23 out')[0]??''
  const previousInvested=[...previousTransactions.matchAll(/\+(\d+(?:\.\d+)?)/g)].reduce((sum,match)=>sum+Number(match[1]),0)
  const previousNet=Number(previous.match(/net([\d.]+)/)?.[1]??0)
  const previousReturn=previousNet&&previousInvested?previousNet-previousInvested:0
  const reported=notes.match(/ABYAN_RETURNS_V1\|asof=([^|]+)\|since=([^|]+)\|market=(-?[\d.]+)\|profits=(-?[\d.]+)\|total=(-?[\d.]+)\|base_value=(-?[\d.]+)\|base_cycle=(-?[\d.]+)\|contributed=(-?[\d.]+)/)
  const lifetimeInvested=reported?Number(reported[8]):invested+previousInvested
  const totalReturn=reported?Number(reported[5])+currentCycleReturn-Number(reported[7]):currentCycleReturn+previousReturn
  const priceReturn=totalReturn-reinvested
  const allocationText=notes.split(';alloc ')[1]??''
  const components=[...allocationText.matchAll(/([A-Z][A-Z0-9.]*?)(\d+(?:\.\d+)?)%/g)].map(match=>({symbol:match[1],weight:Number(match[2])}))
  return{invested,lifetimeInvested,marketValue,reinvested,totalReturn,currentCycleReturn,priceReturn,totalReturnPercent:lifetimeInvested?totalReturn/lifetimeInvested*100:0,currentCycleReturnPercent:invested?currentCycleReturn/invested*100:0,priceReturnPercent:lifetimeInvested?priceReturn/lifetimeInvested*100:0,previousReturn,reportedSince:reported?.[2]??null,reportedAsOf:reported?.[1]??null,reportedMarket:reported?Number(reported[3]):null,reportedProfits:reported?Number(reported[4]):null,components}
}

export default function AlternativeInvestmentsPage(){
  const financial=useFinancialSummary();const{formatMoney}=useCurrency();const{t,language}=useLanguage()
  const[platforms,setPlatforms]=useState<FinancialPlatform[]>([]);const[items,setItems]=useState<AlternativeInvestment[]>([]);const[open,setOpen]=useState(false);const[error,setError]=useState('');const[activeFamily,setActiveFamily]=useState('ALL');const[expandedPlatform,setExpandedPlatform]=useState('')
  const[form,setForm]=useState({recording_method:'OPENING' as 'BANK'|'OPENING',platform_name:'',investment_name:'',investment_type:'',funding_bank_account_id:'',principal_amount:'',current_value:'',expected_annual_return:'',investment_date:today(),maturity_date:'',next_distribution_date:'',distribution_frequency:'',currency_code:'SAR',transaction_date:nowInput(),notes:''})
  const load=()=>getAlternativeInvestments().then(setItems)
  useEffect(()=>{void load();getFinancialPlatforms().then(setPlatforms)},[])
  const set=(key:string,value:string)=>setForm(current=>({...current,[key]:value}))
  const total=items.reduce((sum,item)=>sum+Number(item.current_value),0)
  const grouped=useMemo(()=>categories.map(category=>({...category,items:items.filter(item=>familyOf(item.investment_type)===category.type)})),[items])
  const visibleGroups=activeFamily==='ALL'?grouped:grouped.filter(group=>group.type===activeFamily)
  const managedByPlatform=useMemo(()=>{
    const buckets=new Map<string,AlternativeInvestment[]>()
    for(const item of items.filter(entry=>familyOf(entry.investment_type)==='MANAGED_PORTFOLIO'))buckets.set(item.platform_name,[...(buckets.get(item.platform_name)??[]),item])
    const portfolioOrder=['Global Portfolio','Family Portfolio','Awqaf Portfolio']
    return [...buckets].map(([platform,portfolios])=>{
      portfolios.sort((a,b)=>{
        const rankA=portfolioOrder.indexOf(a.investment_name)
        const rankB=portfolioOrder.indexOf(b.investment_name)
        if(rankA!==-1||rankB!==-1)return (rankA===-1?Number.MAX_SAFE_INTEGER:rankA)-(rankB===-1?Number.MAX_SAFE_INTEGER:rankB)
        return a.investment_date.localeCompare(b.investment_date)||a.investment_name.localeCompare(b.investment_name)
      })
      const principal=portfolios.reduce((sum,item)=>sum+Number(item.principal_amount),0);const current=portfolios.reduce((sum,item)=>sum+Number(item.current_value),0);const currentCycleReturn=portfolios.reduce((sum,item)=>sum+managedPortfolioMetrics(item).currentCycleReturn,0);const totalReturn=portfolios.reduce((sum,item)=>sum+managedPortfolioMetrics(item).totalReturn,0);return{platform,portfolios,principal,current,currentCycleReturn,totalReturn,returnPercent:principal?currentCycleReturn/principal*100:0}
    })
  },[items])
  const selected=categories.find(category=>category.type===familyOf(form.investment_type))
  const eligiblePlatforms=useMemo(()=>platforms.filter(platform=>platformSupports(platform,form.investment_type)).toSorted((a,b)=>(language==='ar'?a.name_ar:a.name).localeCompare(language==='ar'?b.name_ar:b.name,language,{sensitivity:'base'})),[platforms,form.investment_type,language])
  const isDebt=familyOf(form.investment_type)==='DEBT_CROWDFUNDING'
  const isPrivateEquity=familyOf(form.investment_type)==='PRIVATE_EQUITY'
  const isManaged=form.investment_type==='MANAGED_PORTFOLIO'
  const receivesDistributions=isDebt||isManaged||form.investment_type==='REAL_ESTATE_CROWDFUNDING'

  function chooseType(type:string){setForm(current=>{const chosen=platforms.find(platform=>platform.name===current.platform_name||platform.name_ar===current.platform_name);const debt=familyOf(type)==='DEBT_CROWDFUNDING';return {...current,investment_type:type,platform_name:chosen&&platformSupports(chosen,type)?chosen.name:'',maturity_date:'',next_distribution_date:'',distribution_frequency:debt?'AT_MATURITY':'',expected_annual_return:''}})}
  async function submit(event:FormEvent){event.preventDefault();setError('');try{
    await createAlternativeInvestment({...form,funding_bank_account_id:form.recording_method==='OPENING'?null:Number(form.funding_bank_account_id),principal_amount:Number(form.principal_amount),current_value:form.recording_method==='OPENING'?Number(form.current_value||form.principal_amount):null,expected_annual_return:Number(form.expected_annual_return||0),maturity_date:form.maturity_date||null,next_distribution_date:form.next_distribution_date||null,distribution_frequency:form.distribution_frequency||null,notes:form.notes||null})
    setOpen(false);await financial.refresh();await load()
  }catch(reason){setError(t(reason instanceof Error?reason.message:'Unable to add investment.'))}}

  return <section className="investment-products alternative-investments">
    <PageHeader eyebrow={t('Private Markets')} title={t('Alternative Investments')} subtitle={t('Each investment type keeps the fields, lifecycle, and returns that belong to it.')} icon={Building2} actions={<button className="page-header__primary-action" onClick={()=>setOpen(true)}><Plus size={16}/> {t('Add Investment')}</button>}/>
    <div className="investment-products__metrics"><article><span>{t('Active Investments')}</span><strong>{formatDisplayInteger(items.length,language)}</strong></article><article><span>{t('Current Value')}</span><strong><FormattedMoney value={formatMoney(total)}/></strong></article><article><span>{t('Platforms Used')}</span><strong>{formatDisplayInteger(new Set(items.map(item=>item.platform_name)).size,language)}</strong></article></div>
    <nav className="alternative-family-nav" aria-label={language==='ar'?'فئات الاستثمارات':'Investment categories'}>
      <button type="button" className={activeFamily==='ALL'?'is-active':''} onClick={()=>setActiveFamily('ALL')}><strong>{language==='ar'?'كل الفئات':'All categories'}</strong><span>{formatDisplayInteger(items.length,language)} {language==='ar'?'أصل':'assets'}</span><b><FormattedMoney value={formatMoney(total)}/></b></button>
      {grouped.map(group=>{const Icon=group.icon;const value=group.items.reduce((sum,item)=>sum+Number(item.current_value),0);return <button type="button" key={group.type} className={activeFamily===group.type?'is-active':''} onClick={()=>setActiveFamily(group.type)}><span className="alternative-family-nav__title"><Icon size={15}/><strong>{t(group.title)}</strong></span><span>{formatDisplayInteger(group.items.length,language)} {language==='ar'?'أصل':'assets'}</span><b><FormattedMoney value={formatMoney(value)}/></b></button>})}
    </nav>
    <div className={`alternative-families${activeFamily!=='ALL'?' alternative-families--single':''}`}>
      {visibleGroups.map(group=>{
        const Icon=group.icon
        const value=group.items.reduce((sum,item)=>sum+Number(item.current_value),0)
        return <section key={group.type} className={`alternative-family${group.type==='MANAGED_PORTFOLIO'?' alternative-family--managed':''}`}>
          <header><span><Icon size={18}/></span><div><h2>{t(group.title)}</h2><p>{t(group.description)}</p></div><strong><FormattedMoney value={formatMoney(value)}/></strong></header>
          {group.items.length?group.type==='MANAGED_PORTFOLIO'?<div className="managed-platform-list">
            {managedByPlatform.map(platform=>{
              const isExpanded=expandedPlatform===platform.platform
              return <section className="managed-platform-card" key={platform.platform}>
                <button type="button" className="managed-platform-card__header" aria-expanded={isExpanded} onClick={()=>setExpandedPlatform(isExpanded?'':platform.platform)}>
                  <span className="managed-platform-card__identity"><BrokerLogo name={platform.platform}/><span><strong>{platform.platform}</strong><small>{formatDisplayInteger(platform.portfolios.length,language)} {language==='ar'?'محافظ':'portfolios'}</small></span></span>
                  <span className="managed-platform-card__totals">
                    <span><small>{language==='ar'?'إجمالي الاستثمار الحالي':'CURRENTLY INVESTED'}</small><strong><FormattedMoney value={formatMoney(platform.principal)}/></strong></span>
                    <span><small>{language==='ar'?'القيمة الحالية':'CURRENT VALUE'}</small><strong><FormattedMoney value={formatMoney(platform.current)}/></strong></span>
                    <span className="managed-platform-card__performance"><small>{language==='ar'?'أداء الدورة الحالية':'CURRENT PERFORMANCE'}</small><strong className={platform.currentCycleReturn>=0?'is-positive':'is-negative'}>{formatDisplayPercent(platform.returnPercent,2,language)}</strong></span>
                  </span>
                  <ChevronDown className={isExpanded?'is-expanded':''} size={18}/>
                </button>
                {isExpanded?<div className="managed-platform-card__portfolios">
                  <div className="managed-platform-card__table-head"><span>{language==='ar'?'المحفظة':'PORTFOLIO'}</span><span>{language==='ar'?'استثمار الدورة':'ACTIVE CYCLE INVESTED'}</span><span>{language==='ar'?'القيمة الحالية':'CURRENT VALUE'}</span><span>{language==='ar'?'عائد الدورة':'CURRENT CYCLE RETURN'}</span><span>{language==='ar'?'منذ البداية':'SINCE START RETURN'}</span></div>
                  {platform.portfolios.map(item=>{
                    const metrics=managedPortfolioMetrics(item)
                    return <article key={item.id}>
                      <div><strong>{item.investment_name}</strong><small>{language==='ar'?'منذ':'Since'} {formatDate(item.investment_date)}</small></div>
                      <strong><FormattedMoney value={formatMoney(item.principal_amount,item.currency_code as Currency)}/></strong>
                      <strong><FormattedMoney value={formatMoney(item.current_value,item.currency_code as Currency)}/></strong>
                      <strong className={metrics.currentCycleReturn>=0?'is-positive':'is-negative'}><FormattedMoney value={formatMoney(metrics.currentCycleReturn,item.currency_code as Currency)}/></strong>
                      <div className="managed-platform-card__lifetime-return"><strong className={metrics.totalReturn>=0?'is-positive':'is-negative'}><FormattedMoney value={formatMoney(metrics.totalReturn,item.currency_code as Currency)}/></strong>{metrics.reportedAsOf?<small>{language==='ar'?'بيانات أبيان حتى':'Abyan data through'} {formatDate(metrics.reportedAsOf)}</small>:null}</div>
                    </article>
                  })}
                </div>:null}
              </section>
            })}
          </div>:<div className="alternative-family__rows">{group.items.map(item=><article key={item.id}><div><strong>{item.investment_name}</strong><small>{item.platform_name} · {t(typeLabel(item.investment_type))}</small></div><div><small>{t('Current Value')}</small><strong><FormattedMoney value={formatMoney(item.current_value)}/></strong></div><div><small>{t('Expected Return')}</small><strong>{item.expected_annual_return?formatDisplayPercent(item.expected_annual_return,2,language):'—'}</strong></div><div><small>{t('Maturity')}</small><strong>{item.maturity_date?formatDate(item.maturity_date):t('Open Ended')}</strong></div></article>)}</div>:<button type="button" className="alternative-family__empty" onClick={()=>{chooseType(group.type);setOpen(true)}}><Plus size={15}/>{t('Add the first investment in this category')}</button>}
        </section>
      })}
    </div>
    {open?<div className="investment-modal"><form onSubmit={submit}><header><div><h2>{t('Add Alternative Investment')}</h2><p>{selected?t(selected.description):t('Start by choosing the investment family. The form will adapt to it.')}</p></div><button type="button" aria-label={t('Close')} onClick={()=>setOpen(false)}><X size={17}/></button></header>
      <div className="alternative-type-picker">{categories.map(category=>{const Icon=category.icon;return <button type="button" className={familyOf(form.investment_type)===category.type?'is-active':''} onClick={()=>chooseType(category.type)} key={category.type}><Icon size={18}/><span>{t(category.title)}</span></button>})}</div>
      {form.investment_type?<div className="investment-form-grid">
        <label className="is-wide"><span>{t('Recording method')}</span><select value={form.recording_method} onChange={e=>setForm(current=>({...current,recording_method:e.target.value as 'BANK'|'OPENING',funding_bank_account_id:'',current_value:''}))}><option value="OPENING">{t('Existing investment — opening balance')}</option><option value="BANK">{t('New investment — funded from bank')}</option></select></label>
        <label><span>{t('Platform')}</span><select required value={form.platform_name} onChange={e=>set('platform_name',e.target.value)}><option value="">{t('Select a compatible platform')}</option>{eligiblePlatforms.map(item=><option key={item.code} value={item.name}>{language==='ar'?item.name_ar:item.name}</option>)}</select>{!eligiblePlatforms.length?<small><Link to="/operations/add-investment-platform">{t('No added platform supports this investment type. Add a compatible platform.')}</Link></small>:<small>{t('Only platforms supporting the selected investment type are shown.')}</small>}</label>
        <label><span>{t(isManaged?'Portfolio Name':'Investment Name')}</span><input required value={form.investment_name} onChange={e=>set('investment_name',e.target.value)}/></label>
        {form.recording_method==='BANK'?<label><span>{t('Funding Bank')}</span><select required value={form.funding_bank_account_id} onChange={e=>set('funding_bank_account_id',e.target.value)}><option value="">{t('Select Account')}</option>{financial.data?.bank_accounts.map(account=><option key={account.id} value={account.id}>{account.account_name} · {formatMoney(account.current_balance)}</option>)}</select></label>:null}
        <label><span>{t(isManaged?'Amount Invested':'Principal Amount')}</span><input required type="number" min="0.01" step="0.01" value={form.principal_amount} onChange={e=>set('principal_amount',e.target.value)}/></label>
        {form.recording_method==='OPENING'?<label><span>{t('Current Value')}</span><input required type="number" min="0.01" step="0.01" value={form.current_value} onChange={e=>set('current_value',e.target.value)}/></label>:null}
        <label><span>{t('Currency')}</span><select value={form.currency_code} onChange={e=>set('currency_code',e.target.value)}><option value="SAR">SAR</option><option value="USD">USD</option><option value="AED">AED</option></select></label>
        <label><span>{t('Investment Date')}</span><DateInput required type="date" value={form.investment_date} onChange={e=>set('investment_date',e.target.value)}/></label>
        {isPrivateEquity?<label><span>{t('Investment subtype')}</span><select value={form.investment_type} onChange={e=>{set('investment_type',e.target.value);set('platform_name','')}}>{['PRIVATE_EQUITY','VENTURE_CAPITAL','EQUITY_CROWDFUNDING'].map(value=><option key={value} value={value}>{t(typeLabel(value))}</option>)}</select></label>:null}
        {isDebt?<label><span>{t('Investment subtype')}</span><select value={form.investment_type} onChange={e=>{set('investment_type',e.target.value);set('platform_name','')}}>{['DEBT_CROWDFUNDING','PRIVATE_FUND','PRIVATE_SUKUK','P2P_LENDING'].map(value=><option key={value} value={value}>{t(typeLabel(value))}</option>)}</select></label>:null}
        {isDebt?<label><span>{t('Maturity Date')}</span><DateInput required type="date" value={form.maturity_date} onChange={e=>set('maturity_date',e.target.value)}/></label>:null}
        {form.investment_type!=='VENTURE_CAPITAL'?<label><span>{t('Expected Annual Return %')}</span><input type="number" min="0" step="0.01" value={form.expected_annual_return} onChange={e=>set('expected_annual_return',e.target.value)}/></label>:null}
        {receivesDistributions?<><label><span>{t('Distribution Frequency')}</span><select value={form.distribution_frequency} onChange={e=>set('distribution_frequency',e.target.value)}><option value="">{t('No scheduled distributions')}</option>{['WEEKLY','MONTHLY','QUARTERLY','SEMI_ANNUAL','ANNUAL','AT_MATURITY'].map(value=><option key={value} value={value}>{t(typeLabel(value))}</option>)}</select></label>{form.distribution_frequency&&form.distribution_frequency!=='AT_MATURITY'?<label><span>{t('Next Distribution')}</span><DateInput type="date" value={form.next_distribution_date} onChange={e=>set('next_distribution_date',e.target.value)}/></label>:null}</>:null}
        <label className="is-wide"><span>{t('Notes')}</span><input value={form.notes} onChange={e=>set('notes',e.target.value)}/></label>
      </div>:<div className="alternative-type-prompt">{t('Choose an investment category to continue.')}</div>}
      {error?<p className="investment-form-error">{error}</p>:null}<footer><button type="button" onClick={()=>setOpen(false)}>{t('Cancel')}</button><button type="submit" disabled={!form.investment_type}>{t('Add Investment')}</button></footer></form></div>:null}
  </section>
}
