import { apiPost } from './api'

type WithdrawCashRequest = {
  portfolio_id: number
  destination_bank_account_id: number
  amount: number
  transaction_date: string
  description: string
}

export async function withdrawCash(
  request: WithdrawCashRequest,
) {
  return apiPost(
    '/accounting/withdraw-cash',
    request,
  )
}
