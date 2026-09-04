import { Info } from 'lucide-react'

import './FinancialHealthCard.css'
import { formatDisplayPercent } from '../../utils/localeFormat'
import { useLanguage } from '../../context/LanguageContext'
import FormattedMoney from '../ui/FormattedMoney'

type FinancialHealthCardProps = {
  dbr: number
  score: number
  cash: string
  investments: string
  riskLevel: 'LOW' | 'MODERATE' | 'HIGH'
}

export default function FinancialHealthCard({
  dbr,
  score,
  cash,
  investments,
  riskLevel,
}: FinancialHealthCardProps) {
  const {t}=useLanguage()
  const riskClass = `is-${riskLevel.toLowerCase()}`
  const healthLabel = score >= 80 ? 'Healthy' : score >= 60 ? 'Watch' : 'At Risk'
  return (
    <section className="financial-health" aria-label="Financial health summary">
      <div className="financial-health__indicators">
        <div className="financial-health__score" aria-label={`Financial health score ${score} out of 100`}>
          <small className="financial-health__indicator-label">{t('Health Score')}</small>
          <div><strong>{score}</strong><span>/100</span></div>
          <em className="financial-health__substatus">{t(healthLabel)}</em>
        </div>

        <div className="financial-health__cash">
          <span className="financial-health__indicator-label">{t('Available Cash')}</span>
          <strong><FormattedMoney value={cash}/></strong>
          <small className="financial-health__substatus">{t('Liquidity')}</small>
        </div>

        <div className="financial-health__investments">
          <span className="financial-health__indicator-label">{t('Investments')}</span>
          <strong><FormattedMoney value={investments}/></strong>
          <small className="financial-health__substatus">{t('Invested Assets')}</small>
        </div>

        <div className="financial-health__metric">
          <div className="financial-health__metric-label">
            <span className="financial-health__indicator-label">DBR</span>
            <button type="button" aria-label="What is Debt Burden Ratio?" className="financial-health__info">
              <Info size={13} />
              <span role="tooltip">
                <strong>Debt Burden Ratio</strong>
                The percentage of monthly income used to meet recurring debt payments.
              </span>
            </button>
          </div>
          <strong>{formatDisplayPercent(dbr)}</strong>
          <small className="financial-health__status financial-health__substatus">{t(dbr < 25 ? 'Healthy' : dbr < 40 ? 'Moderate' : 'High')}</small>
        </div>

        <div className="financial-health__risk">
          <span className={`financial-health__risk-dot ${riskClass}`} />
          <span className="financial-health__indicator-label">{t('Risk Level')}</span>
          <strong className={riskClass}>{t(riskLevel.charAt(0) + riskLevel.slice(1).toLowerCase())}</strong>
          <small aria-hidden="true">&nbsp;</small>
        </div>
      </div>
    </section>
  )
}
