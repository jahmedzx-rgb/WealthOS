import StatCard from '../ui/StatCard'
import StatGrid from '../ui/StatGrid'

type Props = {
  totalCost: number
  marketValue: number
  unrealizedPL: number
  positionsCount: number
}

export default function PortfolioSummaryCard({
  totalCost,
  marketValue,
  unrealizedPL,
  positionsCount,
}: Props) {
  return (
    <StatGrid>
      <StatCard
        title="Total Cost"
        value={`$${totalCost.toFixed(2)}`}
      />

      <StatCard
        title="Market Value"
        value={`$${marketValue.toFixed(2)}`}
      />

      <StatCard
        title="Unrealized P/L"
        value={`$${unrealizedPL.toFixed(2)}`}
      />

      <StatCard
        title="Positions"
        value={positionsCount.toString()}
      />
    </StatGrid>
  )
}
