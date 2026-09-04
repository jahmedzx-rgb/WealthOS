import { ArrowUpRight, Landmark, Plus, WalletCards } from 'lucide-react'
import { Link } from 'react-router-dom'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import './CashPage.css'
import './InvestingSubpages.css'

export default function CashPage(){
  const financial=useFinancialSummary();const{formatMoney}=useCurrency();const{t}=useLanguage();const data=financial.data
  const cashType=(code:number)=>t(code===1110?'Cash on hand':code===1120?'Bank cash':code===1130?'Brokerage cash':'Cash account')
  const cashOnHand=data?.cash_accounts.find(item=>item.code===1110)?.balance??0
  const bankCash=data?.bank_account_summary.total_balance??0
  const brokerageCash=data?.cash_accounts.find(item=>item.code===1130)?.balance??0
  if(financial.loading)return <main className="cash-page__state">{t('Loading cash…')}</main>
  if(financial.error||!data)return <main className="cash-page__state">{t('Unable to load cash:')} {financial.error}</main>
  return <section className="cash-page">
    <PageHeader className="cash-page__header" eyebrow={t('Cash Assets')} title={t('Cash')} subtitle={t('View cash on hand, bank balances, and brokerage cash in one place.')} icon={WalletCards} actions={<Link className="page-header__primary-action" to="/operations/transfer"><ArrowUpRight size={16}/> {t('Move Cash')}</Link>}/>
    <div className="cash-page__metrics"><article><span>{t('Total Cash')}</span><strong><FormattedMoney value={formatMoney(data.available_cash)}/></strong><small>{t('Available across cash accounts')}</small></article><article><span>{t('Cash on hand')}</span><strong><FormattedMoney value={formatMoney(cashOnHand)}/></strong><small>{t('Physical cash asset')}</small></article><article><span>{t('Bank balances')}</span><strong><FormattedMoney value={formatMoney(bankCash)}/></strong><small>{data.bank_account_summary.accounts_count} {t('posted accounts')}</small></article><article><span>{t('Brokerage cash')}</span><strong className={brokerageCash<0?'is-negative':''}><FormattedMoney value={formatMoney(brokerageCash)}/></strong><small>{t(brokerageCash<0?'Drawn by investment purchases':'Available for trading')}</small></article></div>
    <section className="cash-page__panel"><header><div><h2>{t('Cash Sources')}</h2><p>{t('Live balances from posted accounting operations.')}</p></div><nav><Link to="/operations/opening-cash"><Plus size={14}/>{t('Cash on hand')}</Link><Link to="/operations/bank-account"><Landmark size={14}/>{t('Bank account')}</Link></nav></header><div className="cash-page__table-head"><span>{t('Source')}</span><span>{t('Classification')}</span><span>{t('Balance')}</span></div>{data.cash_accounts.map(item=><div className="cash-page__row" key={item.code}><span><strong>{item.name}</strong><small>{t('General Ledger')} · {item.code}</small></span><span>{cashType(item.code)}</span><strong className={item.balance<0?'is-negative':''}><FormattedMoney value={formatMoney(item.balance)}/></strong></div>)}</section>
  </section>
}
