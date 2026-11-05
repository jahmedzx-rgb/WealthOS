import { ArrowRight, Search, Workflow } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { useLanguage } from '../context/LanguageContext'
import { operationEngine } from '../operations/operationEngine'
import './OperationsCatalogPage.css'

const categories={accounting:'Cash Flow',investing:'Investing',assets:'Assets',liabilities:'Liabilities'} as const
const impacts:Record<string,string>={income:'Income Recognition',expense:'Expense Recognition',transfer:'Asset Reallocation','add-cash':'Asset Reallocation','withdraw-cash':'Asset Reallocation','opening-cash':'Opening Asset',inheritance:'Inherited Wealth',trade:'Investment Movement','add-broker':'No Financial Impact','add-investment-platform':'No Financial Impact',deposit:'Asset Reallocation','card-payment':'Financing','credit-card-account':'Financing','new-loan':'Financing','manage-loans':'Financing','buy-asset':'Asset Increase','sell-asset':'Asset Decrease','journal-entry':'Depends on Entry','bank-account':'No Financial Impact','bank-card':'No Financial Impact',property:'Asset Increase','property-valuation':'Asset Revaluation'}

export default function OperationsCatalogPage(){
  const {t}=useLanguage()
  const navigate=useNavigate();const location=useLocation();const command=(location.state as{command?:string}|null)?.command
  const [filter,setFilter]=useState('All');const [query,setQuery]=useState('')
  const operations=useMemo(()=>operationEngine.getAll().sort((a,b)=>a.order-b.order),[])
  const visible=useMemo(()=>operations.filter(item=>(filter==='All'||categories[item.category]===filter)&&`${item.title} ${item.description} ${categories[item.category]} ${impacts[item.id]??''}`.toLowerCase().includes(query.toLowerCase())),[operations,filter,query])
  return <section className="operations-catalog">
    <PageHeader title={t('Operations')} subtitle={t('Record, transfer, invest, and manage every financial movement.')} icon={Workflow}/>
    <div className="operations-catalog__metrics"><article><span>{t('Available Operations')}</span><strong>{operations.length}</strong><small>{t('Across the Workspace')}</small></article><article><span>{t('Ready to Use')}</span><strong>{operations.filter(item=>item.status==='active').length}</strong><small>{t('Connected Workflows')}</small></article><article><span>{t('Categories')}</span><strong>{new Set(operations.map(item=>item.category)).size}</strong><small>{t('Organized by Financial Purpose')}</small></article></div>
    {command&&<div className="operations-catalog__command"><span>{t('Command Received')}</span><strong>{command}</strong><small>{t('Select the matching operation to continue.')}</small></div>}
    <section className="operations-catalog__panel">
      <div className="operations-catalog__toolbar"><label><Search size={17}/><input value={query} onChange={event=>setQuery(event.target.value)} placeholder={t('Search Operations')}/></label><nav>{['All','Cash Flow','Investing','Assets','Liabilities'].map(value=><button className={filter===value?'is-active':''} type="button" onClick={()=>setFilter(value)} key={value}>{t(value)}</button>)}</nav></div>
      <div className="operations-catalog__columns"><span>{t('Operation')}</span><span>{t('Category')}</span><span>{t('Financial Impact')}</span><span>{t('Availability')}</span><i/></div>
      <div className="operations-catalog__list">{visible.map(operation=>{const Icon=operation.icon;const available=operation.status==='active';return <button key={operation.id} type="button" disabled={!available} onClick={()=>{if(available)navigate(operation.route)}}><span className={`operations-catalog__icon is-${operation.category}`}><Icon size={18}/></span><span className="operations-catalog__copy"><strong>{t(operation.title)}</strong><small>{t(operation.description)}</small></span><span className="operations-catalog__meta"><small>{t('Category')}</small><strong>{t(categories[operation.category])}</strong></span><span className="operations-catalog__meta"><small>{t('Financial Impact')}</small><strong>{t(impacts[operation.id]??'To Be Defined')}</strong></span><span className={`operations-catalog__status is-${operation.status}`}>{t(available?'Available':'Coming Soon')}</span><ArrowRight size={17}/></button>})}</div>
      {!visible.length&&<div className="operations-catalog__empty">{t('No Operations Match This Search.')}</div>}
    </section>
  </section>
}
