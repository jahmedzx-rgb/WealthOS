import type { ComponentProps } from 'react'
import LookupSelect from './LookupSelect'

export default function LoanBankLookup(props: ComponentProps<typeof LookupSelect>) {
  return <LookupSelect {...props} menuPlacement="top" />
}
