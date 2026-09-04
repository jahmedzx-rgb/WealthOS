import "./AllocationChart.css"

type Props = {
  allocation: Record<string, number>
}

export default function AllocationChart({
  allocation,
}: Props) {
  return (
    <div className="allocation-chart">
      {Object.entries(allocation).map(([assetType, weight]) => {
        const percentage = weight * 100

        return (
          <div
            key={assetType}
            className="allocation-chart__item"
          >
            <div className="allocation-chart__row">
              <span className="allocation-chart__label">
                {assetType}
              </span>

              <span className="allocation-chart__value">
                {percentage.toFixed(2)}%
              </span>
            </div>

            <div className="allocation-chart__track">
              <div
                className="allocation-chart__bar"
                style={{
                  width: `${Math.min(Math.max(percentage, 0), 100)}%`,
                }}
              />
            </div>
          </div>
        )
      })}
    </div>
  )
}
