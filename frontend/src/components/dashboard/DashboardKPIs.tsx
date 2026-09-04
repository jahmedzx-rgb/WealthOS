import StatGrid from '../ui/StatGrid'
import StatCard from '../ui/StatCard'

type Props = {
  netWorth: string
  portfolioValue: string
  cash: string
  totalReturn: string
  totalReturnPercentage: string
}

export default function DashboardKPIs({
  netWorth,
  portfolioValue,
  cash,
  totalReturn,
  totalReturnPercentage,
}: Props) {
  return (
    <StatGrid>
      <StatCard
        title="Net Worth"
        value={netWorth}
      />

      <StatCard
        title="Portfolio"
        value={portfolioValue}
      />

      <StatCard
        title="Cash"
        value={cash}
      />

      <StatCard
        title="Total Return"
        value={totalReturn}
        subtitle={totalReturnPercentage}
      />
    </StatGrid>
  )
}
