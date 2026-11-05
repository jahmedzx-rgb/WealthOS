import { ArrowUpRight, ChartNoAxesCombined, Landmark, RefreshCcw, Scale, WalletCards } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { useLanguage } from '../context/LanguageContext'
import './AccountingPage.css'
import './AccountingTabs.css'
import LoansView from './LoansView'

export default function LoansAccountingPage(){
  const {t}=useLanguage()
  const navigate=useNavigate()
  return <section className="accounting-page">
    <PageHeader title={t('Accounting')} subtitle={t('Understand your cash movement and consolidated financial position.')} icon={WalletCards}/>
    <nav className="accounting-page__tabs" aria-label={t('Accounting views')}>
      <button onClick={()=>navigate('/accounting')}><ArrowUpRight size={16}/>{t('Cash Flow')}</button>
      <button onClick={()=>navigate('/accounting?tab=position')}><Scale size={16}/>{t('Balance Sheet')}</button>
      <button onClick={()=>navigate('/accounting?tab=income')}><ChartNoAxesCombined size={16}/>{t('Income Statement')}</button>
      <button className="is-active"><Landmark size={16}/>{t('Liabilities & Loans')}</button>
      <button onClick={()=>navigate('/accounting/reconciliation')}><RefreshCcw size={16}/>{t('Reconciliation')}</button>
    </nav>
    <LoansView/>
  </section>
}
