import { apiPost } from './api'

type TransferRequest = {
  from_account_code: number
  to_account_code: number
  from_bank_account_id?: number
  to_bank_account_id?: number
  amount: number
  transaction_date: string
  description: string
}

export async function transfer(
  request: TransferRequest,
) {
  return apiPost(
    '/accounting/transfer',
    request,
  )
}
