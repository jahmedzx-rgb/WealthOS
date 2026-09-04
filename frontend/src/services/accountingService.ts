import { apiDelete, apiGet, apiPatch, apiPost, apiPut } from './api'

type AddCashRequest = {
  portfolio_id: number
  source_bank_account_id: number
  amount: number
  transaction_date: string
  description: string
}

export async function addCash(
  request: AddCashRequest,
) {
  return apiPost(
    '/accounting/add-cash',
    request,
  )
}

type IncomeRequest = {
  income_source: string
  accounting_category?: string
  destination_account_code: number
  destination_bank_account_id?: number
  amount: number
  transaction_date: string
  description: string
  linked_source?: string
  rent_frequency?: 'MONTHLY'|'QUARTERLY'|'SEMI_ANNUAL'|'ANNUAL'
  next_rent_due_date?: string
  rent_property_name?: string
}

export async function recordIncome(request: IncomeRequest) {
  return apiPost('/accounting/income', request)
}
export type PropertyIncomeType = 'RESIDENTIAL_RENT'|'COMMERCIAL_RENT'|'SHORT_TERM_RENT'
export type PropertyAsset = { id:number;reference:string;name:string;usage:'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER'|'UNSPECIFIED';income_type:PropertyIncomeType|null;acquisition_cost:number;current_value:number;purchase_date:string }
export const getProperties = () => apiGet<PropertyAsset[]>('/accounting/properties')
export const updateProperty = (id:number,request:{property_name:string;property_usage:'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER';property_income_type:PropertyIncomeType|null}) => apiPatch<PropertyAsset>(`/accounting/properties/${id}`,request)
export const adjustPropertyValue = (id:number,request:{corrected_value:number;adjustment_date:string;reason:string}) => apiPost<PropertyAsset>(`/accounting/properties/${id}/value-adjustment`,request)
export type RentalReminder = { id:number;property_reference:string;property_name:string;expected_amount:number;frequency:string;next_due_date:string;destination_account_code:number;days_until:number }
export const getRentalReminders = (days=30) => apiGet<RentalReminder[]>(`/accounting/rental-reminders?days=${days}`)

export type Loan = { id:number; name:string; lender:string; loan_type:string; principal_amount:number; outstanding_balance:number; amount_received:number; fees:number; annual_rate:number; term_months:number; monthly_payment:number; first_payment_date:string; status:string }
export type LoanRequest = Omit<Loan, 'id'|'outstanding_balance'|'status'> & { destination_account_code:number;destination_bank_account_id:number }
export const createLoan = (request:LoanRequest) => apiPost<Loan>('/accounting/loans', request)
export const getLoans = () => apiGet<Loan[]>('/accounting/loans')
export const updateLoan = (id:number,request:{name:string;lender:string;annual_rate:number;term_months:number;monthly_payment:number;first_payment_date:string}) => apiPatch<Loan>(`/accounting/loans/${id}`,request)
export const voidLoan = (id:number) => apiPost<Loan>(`/accounting/loans/${id}/void`,{})
export const settleLoan = (id:number,settlement_amount:number,payment_bank_account_id:number) => apiPost<Loan>(`/accounting/loans/${id}/settle`,{settlement_amount,payment_account_code:1120,payment_bank_account_id})
export const refinanceLoan = (id:number,request:{lender:string;principal_amount:number;fees:number;annual_rate:number;term_months:number;monthly_payment:number;first_payment_date:string;loan_type:string;bank_account_code:number;bank_account_id:number}) => apiPost<Loan>(`/accounting/loans/${id}/refinance`,request)

export type BalanceItem = { code:number; name:string; balance:number }
export type FinancialActivity = { id:number; description:string; transaction_date:string; cash_change:number; related_reference:string|null }
export type CreditCardSummary = { cards_count:number; total_limit:number; used:number; available:number; utilization:number; monthly_obligation:number }
export type CreditCardAccount = { id:number; issuer_bank:string; card_name:string; last4:string; credit_limit:number; current_balance:number; statement_balance:number; minimum_monthly_payment:number; statement_cutoff_day:number|null; payment_due_day:number|null; is_fee_free:boolean; annual_fee:number; fee_renewal_day:number|null; fee_renewal_month:number|null; currency_code:string }
export type BankAccountSummary = { accounts_count:number; total_balance:number; monthly_inflow:number; monthly_outflow:number }
export type BankAccount = { id:number; bank_name:string; account_type:string; account_name:string; account_identifier:string; display_name?:string; current_balance:number; currency_code:string; is_primary:boolean; has_opening_balance:boolean; opening_balance:number; opening_balance_date:string|null }
export const getBankAccounts = () => apiGet<BankAccount[]>('/accounting/bank-accounts')
export const getBankAccount = (id:number) => apiGet<BankAccount>(`/accounting/bank-accounts/${id}`)
export const updateBankAccount = (id:number,request:{bank_name:string;account_type:string;account_name?:string;account_identifier:string;correction_reason:string}) => apiPut<BankAccount>(`/accounting/bank-accounts/${id}`,request)
export const setBankOpeningBalance = (id:number,request:{corrected_opening_balance:number;opening_date:string;adjustment_date:string;reason:string}) => apiPost<{bank_account_id:number;previous_opening_balance:number;corrected_opening_balance:number;difference_posted:number;current_balance:number;posting_date:string;prior_period_adjustment:boolean;journal_entry_id:number}>(`/accounting/bank-accounts/${id}/opening-balance`,request)
export type Deposit = { id:number;provider_name:string;product_name:string;product_type:'TERM_DEPOSIT'|'INCOME_SAVINGS';funding_bank_account_id:number;income_bank_account_id:number|null;principal_amount:number;current_balance:number;annual_return_rate:number;payout_frequency:string;start_date:string;maturity_date:string|null;auto_renew:boolean;currency_code:string;status:string }
export type FinancialSummary = { rental_income_ttm:number; real_estate_return:number; total_assets:number; total_liabilities:number; net_worth:number; available_cash:number; monthly_income:number; monthly_expenses:number; income_breakdown:BalanceItem[]; expense_breakdown:BalanceItem[]; cash_inflow:number; cash_outflow:number; net_cash_flow:number; monthly_debt_payments:number; dbr:number; health_score:number; risk_level:'LOW'|'MODERATE'|'HIGH'; asset_breakdown:BalanceItem[]; liability_breakdown:BalanceItem[]; cash_accounts:BalanceItem[]; recent_activity:FinancialActivity[]; credit_cards:CreditCardAccount[]; credit_card_summary:CreditCardSummary; bank_accounts:BankAccount[]; bank_account_summary:BankAccountSummary; deposits:Deposit[]; properties:PropertyAsset[]; accounting_period:{current_period:string;current_status:'CURRENT'|'SAVED';last_closed_period:string|null} }
export const getFinancialSummary = () => apiGet<FinancialSummary>('/accounting/financial-summary')
export type FinancialReportRow = { code:number|null;label:string;section:string;value:number;is_total:boolean }
export type FinancialReport = { report_type:string;start_date:string;end_date:string;basis:string;source_entry_count:number;generated_at:string;rows:FinancialReportRow[];month_close_id?:number;month_close_checksum?:string }
export const getFinancialReport = (reportType:string,startDate:string,endDate:string) => apiGet<FinancialReport>(`/accounting/reports?report_type=${encodeURIComponent(reportType)}&start_date=${startDate}&end_date=${endDate}`)
export type ReportFrequency='MONTHLY'|'QUARTERLY'|'ANNUAL'
export type PeriodicFinancialReport={report_type:string;frequency:ReportFrequency;periods:Array<{period:string;period_start:string;period_end:string;status:'CURRENT'|'SAVED';report:FinancialReport}>}
export const getPeriodicFinancialReports=(reportType:string,frequency:ReportFrequency,periods:number,endDate:string)=>apiGet<PeriodicFinancialReport>(`/accounting/reports/periodic?report_type=${encodeURIComponent(reportType)}&frequency=${frequency}&periods=${periods}&end_date=${endDate}`)
export type MonthCloseComparison={label:string;ledger:number;operational:number;variance:number;matches:boolean}
export type MonthCloseRecord={id:number;period_start:string;period_end:string;status:'CLOSED'|'REOPENED';snapshot:Record<string,FinancialReport>;checklist:{comparisons:MonthCloseComparison[]};checksum:string;closed_at:string;reopened_at:string|null;reopen_reason:string|null}
export type MonthClosePreview={period_start:string;period_end:string;ready:boolean;later_entries_count:number;unbalanced_entries:Array<{entry_id:number;description:string;debit:number;credit:number}>;comparisons:MonthCloseComparison[];reports:Record<string,FinancialReport>;existing_close:MonthCloseRecord|null}
export const getMonthClosePreview=(year:number,month:number)=>apiGet<MonthClosePreview>(`/accounting/month-closes/preview?year=${year}&month=${month}`)
export const getMonthCloses=()=>apiGet<MonthCloseRecord[]>('/accounting/month-closes')
export const closeMonth=(year:number,month:number)=>apiPost<MonthCloseRecord>('/accounting/month-closes',{year,month})
export const reopenMonth=(id:number,reason:string)=>apiPost<MonthCloseRecord>(`/accounting/month-closes/${id}/reopen`,{reason})
export type JournalLine = {id:number;account_code:number;account_name:string;debit:number;credit:number}
export type JournalEntry = {id:number;transaction_date:string;description:string;related_reference:string|null;created_at:string;lines:JournalLine[]}
export const getJournalEntries = () => apiGet<JournalEntry[]>('/accounting/journal-entries')
export type PostingAccount = { id:number; code:number; name:string; account_type:'ASSET'|'LIABILITY'|'EQUITY'|'REVENUE'|'EXPENSE'; is_cash_account:boolean }
export const getPostingAccounts = () => apiGet<PostingAccount[]>('/accounting/accounts')
export type CardPaymentRequest = { credit_card_id:number; bank_account_id:number; credit_card_account_code:number; payment_account_code:number; amount:number; transaction_date:string; description:string }
export const recordCardPayment = (request:CardPaymentRequest) => apiPost('/accounting/card-payment',request)
export type CreditCardAccountRequest = { issuer_bank:string; card_name:string; last4:string; credit_limit:number; used_balance:number; statement_balance:number; minimum_monthly_payment:number; statement_cutoff_day:number; payment_due_day:number; is_fee_free:boolean; annual_fee:number; fee_renewal_day:number|null; fee_renewal_month:number|null; currency_code:string; as_of_date:string }
export const createCreditCardAccount = (request:CreditCardAccountRequest) => apiPost<CreditCardAccount>('/accounting/credit-cards',request)
export type CreditCardUpdateRequest = { issuer_bank:string;card_name:string;last4:string;credit_limit:number;statement_balance:number;minimum_monthly_payment:number;statement_cutoff_day:number;payment_due_day:number;is_fee_free:boolean;annual_fee:number;fee_renewal_day:number|null;fee_renewal_month:number|null;currency_code:string }
export const updateCreditCard = (id:number, request:CreditCardUpdateRequest) => apiPatch<CreditCardAccount>(`/accounting/credit-cards/${id}`,request)
export const closeCreditCard = (id:number) => apiDelete(`/accounting/credit-cards/${id}`)
export const adjustCreditCardBalance = (id:number,request:{corrected_balance:number;adjustment_date:string;reason:string}) => apiPost<CreditCardAccount>(`/accounting/credit-cards/${id}/balance-adjustment`,request)
export type BankAccountRequest = { bank_name:string; account_type:string; account_name?:string; account_identifier:string; currency_code:string; opening_balance:number; as_of_date:string; is_primary:boolean }
export const createBankAccount = (request:BankAccountRequest) => apiPost<BankAccount>('/accounting/bank-accounts',request)
export type BankCard = {id:number;bank_account_id:number;card_name:string;last4:string;card_network:string;currency_code:string;created_at:string}
export const createBankCard = (request:{bank_account_id:number;card_name:string;last4:string;card_network:string}) => apiPost<BankCard>('/accounting/bank-cards',request)
export type ReconciliationItem={id:number;date:string|null;description:string;amount:number|null;currency:string;status:'MATCHED'|'SUGGESTED'|'REVIEW';posting_reference:string|null;journal_entry_id:number|null;journal_description:string|null}
export type ReconciliationSummary={matched:number;suggested:number;needs_review:number;generated_at:string;items:ReconciliationItem[]}
export const getReconciliation=()=>apiGet<ReconciliationSummary>('/accounting/reconciliation')
export type DepositRequest = {provider_name:string;product_name:string;product_type:'TERM_DEPOSIT'|'INCOME_SAVINGS';funding_bank_account_id:number;income_bank_account_id:number|null;principal_amount:number;annual_return_rate:number;payout_frequency:'MONTHLY'|'QUARTERLY'|'AT_MATURITY';start_date:string;maturity_date:string|null;auto_renew:boolean;currency_code:string;transaction_date:string}
export const createDeposit = (request:DepositRequest) => apiPost<Deposit>('/accounting/deposits',request)
export const getDeposits = () => apiGet<Deposit[]>('/accounting/deposits')
export type DepositUpdateRequest = Pick<DepositRequest,'provider_name'|'product_name'|'product_type'|'income_bank_account_id'|'annual_return_rate'|'payout_frequency'|'start_date'|'maturity_date'|'auto_renew'>
export const updateDeposit = (id:number,request:DepositUpdateRequest) => apiPatch<Deposit>(`/accounting/deposits/${id}`,request)
export const adjustDepositBalance = (id:number,request:{corrected_balance:number;adjustment_date:string;reason:string}) => apiPost<Deposit>(`/accounting/deposits/${id}/balance-adjustment`,request)
export const breakDeposit = (id:number,request:{destination_bank_account_id:number;amount_received:number;transaction_date:string;reason:string}) => apiPost<{message:string;deposit_id:number;amount_received:number;closure_cost:number}>(`/accounting/deposits/${id}/break`,request)
export type JournalEntryRequest = { transaction_date:string; description:string; related_reference?:string; lines:Array<{account_code:number;debit:number;credit:number}> }
export const postJournalEntry = (request:JournalEntryRequest) => apiPost('/accounting/journal-entry',request)
export type ExpenseRequest = { expense_account_code:number;payment_bank_account_id:number;property_id:number|null;amount:number;transaction_date:string;description:string }
export const recordExpense = (request:ExpenseRequest) => apiPost('/accounting/expense',request)
export type PropertyPurchaseRequest = { property_account_code:number; property_name:string; property_usage:'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER'; property_income_type:PropertyIncomeType|null; payment_source:'BANK_ACCOUNT'|'CASH_ON_HAND'; bank_account_id:number|null; amount:number; transfer_tax:number; transaction_date:string; description:string }
export const recordPropertyPurchase = (request:PropertyPurchaseRequest) => apiPost('/accounting/buy-property',request)
export const sellProperty = (id:number,request:{payment_method:'BANK_TRANSFER'|'CHEQUE'|'CASH';payment_destination:'BANK_ACCOUNT'|'CASH_ON_HAND';bank_account_id:number|null;sale_amount:number;selling_costs:number;transaction_date:string;description:string}) => apiPost<{message:string;property_id:number;net_proceeds:number}>(`/accounting/properties/${id}/sell`,request)
export type OtherAssetPurchaseRequest = { asset_account_code:number; payment_source:'BANK_ACCOUNT'|'CASH_ON_HAND'; bank_account_id:number|null; amount:number; transaction_date:string; description:string }
export const recordOtherAssetPurchase = (request:OtherAssetPurchaseRequest) => apiPost('/accounting/buy-asset',request)
export const addOpeningCash = (request:{amount:number;transaction_date:string;description:string}) => apiPost('/accounting/opening-cash',request)
export const getOpeningCashStatus = () => apiGet<{initialized:boolean;current_balance:number}>('/accounting/opening-cash/status')
export const adjustOpeningCash = (request:{corrected_balance:number;transaction_date:string;reason:string}) => apiPost<{message:string;journal_entry_id:number;current_balance:number}>('/accounting/opening-cash/adjustment',request)
export type InheritanceRequest = {timing:'BEFORE_WEALTHOS'|'RECEIVED_AFTER_START';asset_type:'CASH_ON_HAND'|'BANK_ACCOUNT'|'PROPERTY'|'VEHICLE'|'INVESTMENT'|'OTHER_ASSET';amount:number;transaction_date:string;description:string;asset_name:string|null;bank_account_id:number|null;property_usage:'PRIMARY_RESIDENCE'|'INVESTMENT_PROPERTY'|'VACATION_HOME'|'OTHER'|null;property_income_type:PropertyIncomeType|null}
export const recordInheritance = (request:InheritanceRequest) => apiPost<{message:string;journal_entry_id:number;related_reference:string}>('/accounting/inheritance',request)

export type SavingCircle = {id:number;platform_name:string;circle_name:string;installment_amount:number;frequency:'WEEKLY'|'MONTHLY';total_installments:number;payout_installment:number;installments_paid:number;amount_received:number;start_date:string;next_payment_date:string|null;payout_date:string|null;funding_bank_account_id:number;status:string}
export type SavingCircleRequest = Omit<SavingCircle,'id'|'amount_received'|'status'> & {transaction_date:string}
export const getSavingCircles=()=>apiGet<SavingCircle[]>('/accounting/saving-circles')
export const createSavingCircle=(request:SavingCircleRequest)=>apiPost<SavingCircle>('/accounting/saving-circles',request)

export type AlternativeInvestment={id:number;platform_name:string;investment_name:string;investment_type:string;funding_bank_account_id:number;principal_amount:number;current_value:number;expected_annual_return:number;amount_returned:number;investment_date:string;maturity_date:string|null;next_distribution_date:string|null;distribution_frequency:string|null;currency_code:string;status:string;notes:string|null}
export type AlternativeInvestmentRequest=Omit<AlternativeInvestment,'id'|'current_value'|'amount_returned'|'status'> & {transaction_date:string}
export const getAlternativeInvestments=()=>apiGet<AlternativeInvestment[]>('/accounting/alternative-investments')
export const createAlternativeInvestment=(request:AlternativeInvestmentRequest)=>apiPost<AlternativeInvestment>('/accounting/alternative-investments',request)
