import type { ReactNode } from 'react'

import './StatGrid.css'

type Props = {
  children: ReactNode
}

export default function StatGrid({
  children,
}: Props) {
  return (
    <div className="stat-grid">
      {children}
    </div>
  )
}
