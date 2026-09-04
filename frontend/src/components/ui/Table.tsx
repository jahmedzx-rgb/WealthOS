import type { ReactNode } from 'react'

import './Table.css'

type Props = {
  children: ReactNode
}

export default function Table({
  children,
}: Props) {
  return (
    <table className="table">
      {children}
    </table>
  )
}
