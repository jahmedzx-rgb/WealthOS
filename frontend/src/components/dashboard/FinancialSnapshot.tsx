import { CreditCard, Landmark } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { FinancialSummary } from '../../services/accountingService'
import Card from '../ui/Card'
import { useCurrency } from '../../context/CurrencyContext'
import FormattedMoney from '../ui/FormattedMoney'
import './FinancialSnapshot.css'
import { useLanguage } from '../../context/LanguageContext'

export default function FinancialSnapshot({ summary }: { summary: FinancialSummary }) {
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const bankSummary = summary.bank_account_summary
  const cardSummary = summary.credit_card_summary
  const cardBalance = cardSummary.used
  const cashMovement = bankSummary.monthly_inflow + bankSummary.monthly_outflow
  const inflowShare = cashMovement > 0 ? bankSummary.monthly_inflow / cashMovement * 100 : 0
  const outflowShare = cashMovement > 0 ? 100 - inflowShare : 0
  return <section className="financial-snapshot" aria-label={t('Bank accounts and credit cards')}>
    <Card icon={Landmark} title={t('Bank Accounts')} action={<Link className="financial-snapshot__link" to="/bank-accounts">{bankSummary.accounts_count} {t('Accounts')} →</Link>}>
      {bankSummary.accounts_count ? <div className="financial-snapshot__credit-summary financial-snapshot__bank-summary">
        <div className="financial-snapshot__credit-values">
          <div><span>{t('Total Balance')}</span><strong className={bankSummary.total_balance<0?'is-used':'is-remaining'}><FormattedMoney value={formatMoney(bankSummary.total_balance)}/></strong></div>
          <div><span>{t('Monthly Inflow')}</span><strong className="is-remaining"><FormattedMoney value={formatMoney(bankSummary.monthly_inflow)}/></strong></div>
          <div><span>{t('Monthly Outflow')}</span><strong className={bankSummary.monthly_outflow>0?'is-used':undefined}><FormattedMoney value={formatMoney(bankSummary.monthly_outflow)}/></strong></div>
        </div>
        <div className="financial-snapshot__credit-track" aria-label={`${inflowShare.toFixed(1)}% inflow share of monthly cash movement`}><span style={{width:`${inflowShare}%`}}/></div>
        <div className="financial-snapshot__credit-caption"><span>{inflowShare.toFixed(1)}% {t('Inflow')}</span><span>{outflowShare.toFixed(1)}% {t('Outflow')}</span></div>
      </div> : <div className="financial-snapshot__credit-empty financial-snapshot__bank-empty">
        <span className="financial-snapshot__icon financial-snapshot__icon--bank"><Landmark size={18}/></span>
        <div><strong>Add Your First Bank Account</strong><p>Define an account to track balances, inflows, outflows, and liquidity.</p></div>
        <Link to="/operations/bank-account">Add Bank Account</Link>
      </div>}
    </Card>
    <Card icon={CreditCard} title={t('Credit Cards')} action={<Link className="financial-snapshot__link" to="/credit-cards">{cardSummary.cards_count} {t('Cards')} →</Link>}>
      {cardSummary.cards_count ? <div className="financial-snapshot__credit-summary">
        <div className="financial-snapshot__credit-values">
          <div><span>{t('Total Limit')}</span><strong><FormattedMoney value={formatMoney(cardSummary.total_limit)}/></strong></div>
          <div><span>{t('Used')}</span><strong className={cardBalance>0?'is-used':undefined}><FormattedMoney value={formatMoney(cardBalance)}/></strong></div>
          <div><span>{t('Remaining')}</span><strong className="is-remaining"><FormattedMoney value={formatMoney(cardSummary.available)}/></strong></div>
        </div>
        <div className="financial-snapshot__credit-track" aria-label={`${cardSummary.utilization.toFixed(1)}% of total credit used`}><span style={{width:`${Math.min(100,cardSummary.utilization)}%`}}/></div>
        <div className="financial-snapshot__credit-caption"><span>{(100-Math.min(100,cardSummary.utilization)).toFixed(1)}% {t('Available')}</span><span>{cardSummary.utilization.toFixed(1)}% {t('Used')}</span></div>
      </div> : <div className="financial-snapshot__credit-empty">
        <span className="financial-snapshot__icon financial-snapshot__icon--card"><CreditCard size={18}/></span>
        <div><strong>Add Your First Credit Card</strong><p>Define its limit and current balance to track utilization, debt, and DBR.</p></div>
        <Link to="/operations/credit-card-account">Add Credit Card</Link>
      </div>}
    </Card>
  </section>
}
