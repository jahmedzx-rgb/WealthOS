import { ChartCandlestick, ChartNoAxesCombined, Layers3 } from 'lucide-react'

import PageHeader from '../components/ui/PageHeader'
import FormattedMoney from '../components/ui/FormattedMoney'
import PositionsTable from '../components/portfolio/PositionsTable'
import { usePortfolio } from '../hooks/usePortfolio'
import { useCurrency } from '../context/CurrencyContext'
import './PositionsPage.css'
import { formatDisplayPercent } from '../utils/localeFormat'
import './InvestingSubpages.css'
import { marketPriceCoverageLabel } from '../utils/marketPriceFreshness'
import { useLanguage } from '../context/LanguageContext'

export default function PositionsPage() {
  const portfolioId = 'consolidated' as const
  const { data, loading, error } = usePortfolio(portfolioId)
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const priceCoverage=data?marketPriceCoverageLabel(data.positions):null
  const localizedCoverage=priceCoverage?.replace('No Market Prices Yet',t('No Market Prices Yet')).replace('Latest Available By Exchange',t('Latest Available By Exchange')).replace('Previous Close',t('Previous Close')).replace('Live',t('Live')).replace('Delayed',t('Delayed')).replace('As Of',t('As Of'))

  if (loading) return <main className="positions-page__state">{t('Loading positions…')}</main>
  if (error) return <main className="positions-page__state">{t('Unable to load positions:')} {t(error)}</main>
  if (!data) return <main className="positions-page__state">{t('No portfolio positions found.')}</main>

  return <section className="positions-page">
    <PageHeader className="positions-page__header" eyebrow={t('Portfolio Management')} title={t('Investment Positions')} subtitle={t('Review listed holdings, market values, allocation, and unrealized performance.')} icon={ChartCandlestick}/>

    <div className="positions-page__metrics">
      <article><span><Layers3 size={15}/>{t('Positions')}</span><strong>{data.summary.positions_count}</strong><small>{data.portfolio.name}</small></article>
      <article><span>{t('Market value')}</span><strong><FormattedMoney value={formatMoney(data.summary.market_value, data.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])}/></strong><small>{localizedCoverage}</small></article>
      <article><span><ChartNoAxesCombined size={15}/>{t('Unrealized return')}</span><strong className={data.summary.unrealized_pl >= 0 ? 'is-positive' : 'is-negative'}><FormattedMoney value={formatMoney(data.summary.unrealized_pl, data.portfolio.base_currency_code as Parameters<typeof formatMoney>[1])}/></strong><small>{formatDisplayPercent(data.summary.total_return_percentage * 100,2)}</small></article>
    </div>

    <PositionsTable portfolioId={portfolioId} positions={data.positions} />
  </section>
}
