import './PositionDetailsPage.css'

import {
  useParams,
} from 'react-router-dom'
import { ChartCandlestick } from 'lucide-react'

import Table from '../components/ui/Table'
import FormattedMoney from '../components/ui/FormattedMoney'
import { formatDate } from '../utils/dateFormat'
import { usePosition } from '../hooks/usePosition'
import { useCurrency } from '../context/CurrencyContext'
import { marketPriceFreshness } from '../utils/marketPriceFreshness'
import PageHeader from '../components/ui/PageHeader'
import { useLanguage } from '../context/LanguageContext'

export default function PositionDetailsPage() {
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const {
    portfolioId,
    securityId,
  } = useParams()

  const parsedPortfolioId = Number(portfolioId)
  const parsedSecurityId = Number(securityId)

  const {
    data,
    loading,
    error,
  } = usePosition(
    parsedPortfolioId,
    parsedSecurityId,
  )

  if (
    !Number.isInteger(parsedPortfolioId) ||
    !Number.isInteger(parsedSecurityId)
  ) {
    return <main>{t('Invalid position route.')}</main>
  }

  if (loading) {
    return <main>{t('Loading position...')}</main>
  }

  if (error) {
    return (
      <main>
        {t('Failed to load position:')} {t(error)}
      </main>
    )
  }

  if (!data) {
    return <main>{t('Position not found.')}</main>
  }

  const costBasis =
    data.quantity * data.average_cost

  const unrealizedPLPercentage =
    costBasis === 0
      ? 0
      : (data.unrealized_pl / costBasis) * 100

  const unrealizedPLClassName =
    data.unrealized_pl >= 0
      ? 'position-details__value position-details__value--positive'
      : 'position-details__value position-details__value--negative'
  const positionCurrency = data.currency_code as Parameters<typeof formatMoney>[1]

  return (
    <section className="position-details">
      <PageHeader eyebrow={t('Portfolio Management')} title={`${data.symbol} · ${data.name}`} subtitle={t('Review this investment position, valuation, performance, and trade history.')} icon={ChartCandlestick}/>

      <dl className="position-details__metrics">
        <div className="position-details__metric">
          <dt>{t('Market Value')}</dt>
          <dd>
            <FormattedMoney value={formatMoney(data.market_value, positionCurrency)}/>
          </dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Quantity')}</dt>
          <dd>{data.quantity}</dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Average Cost')}</dt>
          <dd>
            <FormattedMoney value={formatMoney(data.average_cost, positionCurrency)}/>
          </dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Market Price')}</dt>
          <dd>
            <FormattedMoney value={formatMoney(data.market_price, positionCurrency)}/>
            <small>{t(marketPriceFreshness(data.market_price_date).status)} · {t('Price As Of')} {marketPriceFreshness(data.market_price_date).asOf}</small>
          </dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Cost Basis')}</dt>
          <dd>
            <FormattedMoney value={formatMoney(costBasis, positionCurrency)}/>
          </dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Unrealized P/L')}</dt>
          <dd className={unrealizedPLClassName}>
            <FormattedMoney value={formatMoney(data.unrealized_pl, positionCurrency)}/>
            {' '}
            ({unrealizedPLPercentage.toFixed(2)}%)
          </dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Exchange')}</dt>
          <dd>{data.exchange}</dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Security Type')}</dt>
          <dd>{t(data.security_type)}</dd>
        </div>

        <div className="position-details__metric">
          <dt>{t('Currency')}</dt>
          <dd>{data.currency_code}</dd>
        </div>
      </dl>

      <section className="position-details__trades">
        <header className="position-details__section-header">
          <h2>{t('Trade History')}</h2>
        </header>

        {data.trade_history.length === 0 ? (
          <p className="position-details__empty-state">
            {t('No trades available.')}
          </p>
        ) : (
          <Table>
            <thead>
              <tr>
                <th>{t('Date')}</th>
                <th>{t('Side')}</th>
                <th>{t('Quantity')}</th>
                <th>{t('Price')}</th>
                <th>{t('Commission')}</th>
              </tr>
            </thead>

            <tbody>
              {data.trade_history.map((trade) => (
                <tr key={trade.id}>
                  <td>
                    {formatDate(trade.trade_date)}
                  </td>

                  <td>{t(trade.side)}</td>

                  <td>{trade.quantity}</td>

                  <td>
                    <FormattedMoney value={formatMoney(trade.price, positionCurrency)}/>
                  </td>

                  <td>
                    <FormattedMoney value={formatMoney(trade.commission, positionCurrency)}/>
                  </td>
                </tr>
              ))}
            </tbody>
          </Table>
        )}
      </section>
    </section>
  )
}
