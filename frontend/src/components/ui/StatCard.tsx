import Card from './Card'

import './StatCard.css'
import './StatsCompact.css'

type Props = {
  title: string
  value: string
  subtitle?: string
}

export default function StatCard({
  title,
  value,
  subtitle,
}: Props) {
  return (
    <Card>
      <div className="stat-card">
        <p className="stat-card__title">
          {title}
        </p>

        <div className="stat-card__primary">
          <div className="stat-card__value">
            {value}
          </div>

          {subtitle && (
            <p className="stat-card__subtitle">
              {subtitle}
            </p>
          )}
        </div>
      </div>
    </Card>
  )
}
