import { ArrowUpRight, CalendarDays, Landmark, Plus, Sprout } from 'lucide-react'
import { Link } from 'react-router-dom'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency, type Currency } from '../context/CurrencyContext'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useLanguage } from '../context/LanguageContext'
import './DepositsPage.css'
import { formatDisplayPercent } from '../utils/localeFormat'
import './InvestingSubpages.css'

export default function DepositsPage() {
  const financial = useFinancialSummary()
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const deposits = financial.data?.deposits ?? []
  const total = deposits.reduce((sum, item) => sum + item.current_balance, 0)
  const weightedReturn = total ? deposits.reduce((sum, item) => sum + item.current_balance * item.annual_return_rate, 0) / total : 0
  const nextMaturity = deposits.map(item => item.maturity_date).filter((value): value is string => Boolean(value)).sort()[0]

  if (financial.loading) return <main className="deposits-page__state">{t('Loading deposits…')}</main>
  if (financial.error) return <main className="deposits-page__state">{t('Unable to load deposits')}: {t(financial.error)}</main>

  return <section className="deposits-page">
    <PageHeader className="deposits-page__header" eyebrow={t('Investment Assets')} title={t('Deposits')} subtitle={t('Review balances, expected returns, payout schedules, and maturity dates.')} icon={Sprout} actions={<Link className="page-header__primary-action" to="/operations/deposit"><Plus size={16}/> {t('Add Deposit')}</Link>}/>

    <div className="deposits-page__metrics">
      <article><span><Landmark size={15}/>{t('Active Deposits')}</span><strong>{deposits.length}</strong><small>{t('Currently Tracked')}</small></article>
      <article><span>{t('Total Balance')}</span><strong><FormattedMoney value={formatMoney(total)}/></strong><small>{t('Posted Deposit Assets')}</small></article>
      <article><span>{t('Weighted Annual Return')}</span><strong>{formatDisplayPercent(weightedReturn,2)}</strong><small>{nextMaturity ? `${t('Next Maturity')} · ${nextMaturity}` : t('No Maturity Date')}</small></article>
    </div>

    <section className="deposits-page__panel">
      <header><div><h2>{t('Deposit Positions')}</h2><p>{t('Every active deposit and savings product recorded in WealthOS.')}</p></div></header>
      <div className="deposits-page__table-head"><span>{t('Deposit')}</span><span>{t('Balance')}</span><span>{t('Return')}</span><span>{t('Maturity')}</span><span>{t('Modify')}</span></div>
      {deposits.length ? deposits.map(item => <div className="deposits-page__row" key={item.id}>
        <span><strong>{item.product_name === 'Monthly Deposit' ? t('Monthly Deposit') : <>{item.product_name}</>}</strong><small>{item.provider_name === 'Wadaie' ? t('Wadaie') : item.provider_name} · {t(item.product_type)}</small></span>
        <strong><FormattedMoney value={formatMoney(item.current_balance, item.currency_code as Currency)}/></strong>
        <span className="is-positive">{formatDisplayPercent(item.annual_return_rate,2)}</span>
        <span><CalendarDays size={14}/>{item.maturity_date ?? t('Open Ended')}</span>
        <span className="deposits-page__actions"><Link to={`/operations/deposit?edit=${item.id}`}>{t('Edit')}</Link><Link className="is-disposition" to={`/operations/break-deposit?deposit=${item.id}`}>{t('Break')}</Link></span>
      </div>) : <div className="deposits-page__empty"><Sprout size={22}/><strong>{t('No Deposits Yet')}</strong><p>{t('Add a deposit to track its balance, return, and maturity.')}</p><Link to="/operations/deposit">{t('Add Deposit')} <ArrowUpRight size={14}/></Link></div>}
    </section>
  </section>
}
