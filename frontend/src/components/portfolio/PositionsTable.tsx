import { useNavigate } from 'react-router-dom'

import Card from '../ui/Card'
import Table from '../ui/Table'
import FormattedMoney from '../ui/FormattedMoney'
import { marketName } from '../../utils/marketPriceFreshness'

import './PositionsTable.css'
import { formatDisplayPercent } from '../../utils/localeFormat'

import type { PortfolioSummary } from '../../types/portfolio'
import { useCurrency, type Currency } from '../../context/CurrencyContext'
import { marketPriceFreshness } from '../../utils/marketPriceFreshness'
import FairValueEditor from '../investing/FairValueEditor'
import { useLanguage } from '../../context/LanguageContext'

type Props = {
  portfolioId: number | 'consolidated'
  positions: PortfolioSummary['positions']
}

export default function PositionsTable({
  portfolioId,
  positions,
}: Props) {
  const navigate = useNavigate()
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()

  return (
    <Card title={t('Positions')}>
      <Table>
        <thead>
          <tr>
            <th>{t('Symbol')}</th>
            <th className="positions-table__number">{t('Quantity')}</th>
            <th className="positions-table__number">{t('Price')}</th>
            <th className="positions-table__number">{t('Market Value')}</th>
            <th className="positions-table__number">{t('Fair Value')}</th>
            <th className="positions-table__number">{t('Unrealized P/L')}</th>
            <th className="positions-table__number">{t('Weight')}</th>
          </tr>
        </thead>

        <tbody>
          {positions.map((position) => (
            <tr
              key={position.security_id}
              onClick={() =>
                navigate(
                  `/portfolios/${position.portfolio_id ?? portfolioId}/positions/${position.security_id}`
                )
              }
              style={{ cursor: 'pointer' }}
            >
              <td className="positions-table__symbol">
                {position.symbol}
                <small>{t(marketName(position.exchange))}</small>
              </td>

              <td className="positions-table__number">
                {position.quantity}
              </td>

              <td className="positions-table__number positions-table__price">
                <FormattedMoney value={formatMoney(position.market_price, position.currency_code as Parameters<typeof formatMoney>[1])}/>
                <small>{t(marketPriceFreshness(position.market_price_date).status)}</small>
              </td>

              <td className="positions-table__number">
                <FormattedMoney value={formatMoney(position.market_value, position.currency_code as Parameters<typeof formatMoney>[1])}/>
              </td>

              <td className="positions-table__number"><FairValueEditor portfolioId={position.portfolio_id!} securityId={position.security_id} value={position.fair_value} currency={position.currency_code as Currency}/></td>

              <td
                className={
                  position.unrealized_pl >= 0
                    ? 'positions-table__pl positions-table__pl--positive'
                    : 'positions-table__pl positions-table__pl--negative'
                }
              >
                <FormattedMoney value={formatMoney(position.unrealized_pl, position.currency_code as Parameters<typeof formatMoney>[1])}/>
              </td>

              <td className="positions-table__number">
                {formatDisplayPercent(position.weight * 100, 2)}
              </td>
            </tr>
          ))}
        </tbody>
      </Table>
    </Card>
  )
}
