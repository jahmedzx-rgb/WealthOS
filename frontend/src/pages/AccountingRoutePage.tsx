import { useSearchParams } from 'react-router-dom'
import AccountingPage from './AccountingPage'

export default function AccountingRoutePage(){
  const [params]=useSearchParams()
  return <AccountingPage key={params.toString()||'cashflow'}/>
}
