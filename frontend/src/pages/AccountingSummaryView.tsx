import type { ReactNode } from 'react'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import ReconciliationView from './ReconciliationView'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayPercent } from '../utils/localeFormat'
import type { FinancialReport } from '../services/accountingService'

type Props={type:'income'|'reconciliation';formatMoney:(value:number)=>ReactNode;report?:FinancialReport|null;monthLabel?:string}

export default function AccountingSummaryView({type,formatMoney,report,monthLabel}:Props){
  const financial=useFinancialSummary()
  const {t,language}=useLanguage()
  if(type==='income'){
    const income=report?.rows.find(row=>row.label==='Total Income')?.value??financial.data?.monthly_income??0
    const expenses=report?-(report.rows.find(row=>row.label==='Total Expenses')?.value??0):financial.data?.monthly_expenses??0
    const surplus=income-expenses
    const margin=income?surplus/income*100:0
    const rows=report?.rows.filter(row=>!row.is_total)??[]
    return <div className="accounting-view"><div className="accounting-view__metrics"><article><span>{t('Total Income')}</span><strong>{report?formatMoney(income):t('Loading…')}</strong><small>{monthLabel} · {t('Posted')}</small></article><article><span>{t('Total Expenses')}</span><strong>{report?formatMoney(expenses):t('Loading…')}</strong><small>{monthLabel} · {t('Posted')}</small></article><article><span>{t('Net Surplus')}</span><strong>{report?formatMoney(surplus):t('Loading…')}</strong><small>{income?`${t('Margin')} ${formatDisplayPercent(margin,1,language)}`:t('No posted income')}</small></article></div><section className="accounting-panel"><header><div><h2>{t('Income Statement')}</h2><p>{t('Income and expenses recognized from posted entries')}</p></div><span>{monthLabel}</span></header><div className="accounting-balance-list">{rows.map(row=><div key={`${row.section}-${row.code}-${row.label}`}><span>{row.code?`${row.code} · `:''}{t(row.label)}</span><strong>{row.value<0?<>({formatMoney(Math.abs(row.value))})</>:formatMoney(row.value)}</strong></div>)}{report&&!rows.length?<div><span>{t('No posted income or expenses')}</span><strong>{formatMoney(0)}</strong></div>:null}</div><div className="accounting-total"><span>{t('Net Surplus')}</span><strong>{report?formatMoney(surplus):'—'}</strong></div></section></div>
  }
  return <ReconciliationView/>
}
