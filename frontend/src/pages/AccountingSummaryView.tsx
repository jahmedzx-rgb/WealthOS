import type { ReactNode } from 'react'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import ReconciliationView from './ReconciliationView'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayPercent } from '../utils/localeFormat'

type Props={type:'income'|'reconciliation';formatMoney:(value:number)=>ReactNode}

export default function AccountingSummaryView({type,formatMoney}:Props){
  const financial=useFinancialSummary()
  const {t,language}=useLanguage()
  if(type==='income'){
    const income=financial.data?.monthly_income??0
    const expenses=financial.data?.monthly_expenses??0
    const surplus=income-expenses
    const margin=income?surplus/income*100:0
    return <div className="accounting-view"><div className="accounting-view__metrics"><article><span>{t('Total Income')}</span><strong>{financial.loading?t('Loading…'):formatMoney(income)}</strong><small>{t('Current month · Posted')}</small></article><article><span>{t('Total Expenses')}</span><strong>{financial.loading?t('Loading…'):formatMoney(expenses)}</strong><small>{t('Current month · Posted')}</small></article><article><span>{t('Net Surplus')}</span><strong>{financial.loading?t('Loading…'):formatMoney(surplus)}</strong><small>{income?`${t('Margin')} ${formatDisplayPercent(margin,1,language)}`:t('No posted income')}</small></article></div><section className="accounting-panel"><header><div><h2>{t('Income Statement')}</h2><p>{t('Income and expenses recognized from posted entries')}</p></div><span>{t('This month')}</span></header><div className="accounting-balance-list">{financial.data?.income_breakdown.map(item=><div key={`income-${item.code}`}><span>{t(item.name)}</span><strong>{formatMoney(item.balance)}</strong></div>)}{financial.data?.expense_breakdown.map(item=><div key={`expense-${item.code}`}><span>{t(item.name)}</span><strong>({formatMoney(item.balance)})</strong></div>)}{financial.data&&!financial.data.income_breakdown.length&&!financial.data.expense_breakdown.length?<div><span>{t('No posted income or expenses')}</span><strong>{formatMoney(0)}</strong></div>:null}</div><div className="accounting-total"><span>{t('Net Surplus')}</span><strong>{formatMoney(surplus)}</strong></div></section></div>
  }
  return <ReconciliationView/>
}
