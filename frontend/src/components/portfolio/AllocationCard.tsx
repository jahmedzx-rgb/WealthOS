import Card from '../ui/Card'
import AllocationChart from '../charts/AllocationChart'

type Props = {
  allocation: Record<string, number>
}

export default function AllocationCard({
  allocation,
}: Props) {
  return (
    <Card title="Allocation">
      <AllocationChart
        allocation={allocation}
      />
    </Card>
  )
}
