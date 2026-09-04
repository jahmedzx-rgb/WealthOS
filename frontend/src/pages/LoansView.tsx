import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { HandCoins, Pencil, Plus, RefreshCcw, Trash2, X } from 'lucide-react'
import { getBankAccounts, getLoans, refinanceLoan, settleLoan, updateLoan, voidLoan, type BankAccount, type Loan } from '../services/accountingService'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import FormattedMoney from '../components/ui/FormattedMoney'
import './LoansView.css'
import { formatDisplayInteger } from '../utils/localeFormat'

type Action = { loan: Loan; mode: 'edit' | 'settle' | 'refinance' | 'void' }

export default function LoansView() {
  const [loans, setLoans] = useState<Loan[]>([])
  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [loading, setLoading] = useState(true)
  const [action, setAction] = useState<Action | null>(null)
  const [message, setMessage] = useState('')
  const currency = useCurrency()
  const { t, language } = useLanguage()
  const formatMoney = (value: number) => <FormattedMoney value={currency.formatMoney(value)} />

  async function load() {
    setLoading(true)
    try { setLoans(await getLoans()) } finally { setLoading(false) }
  }

  useEffect(() => {
    Promise.all([getLoans(), getBankAccounts()])
      .then(([loanItems, bankItems]) => { setLoans(loanItems); setBankAccounts(bankItems) })
      .finally(() => setLoading(false))
  }, [])

  const active = loans.filter((loan) => loan.status === 'ACTIVE')
  const outstanding = active.reduce((sum, loan) => sum + Number(loan.outstanding_balance), 0)
  const loanType = (loan: Loan) => t(loan.loan_type === 'SHORT_TERM' ? 'Short term' : loan.loan_type === 'LONG_TERM' ? 'Long term' : 'Mortgage')
  const status = (loan: Loan) => t(loan.status === 'ACTIVE' ? 'Active' : loan.status === 'VOID' ? 'Voided' : loan.status)
  const actionTitle = action ? t(action.mode === 'edit' ? 'Edit loan' : action.mode === 'settle' ? 'Early settlement' : action.mode === 'refinance' ? 'Debt purchase / refinancing' : 'Void loan') : ''

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!action) return
    const data = new FormData(event.currentTarget)
    const selectedBankId = Number(data.get('bank') ?? bankAccounts.find((item) => item.is_primary)?.id ?? bankAccounts[0]?.id)
    setMessage(t('Processing…'))
    try {
      if (action.mode === 'edit') await updateLoan(action.loan.id, { name: String(data.get('name')), lender: String(data.get('lender')), annual_rate: Number(data.get('rate')), term_months: Number(data.get('term')), monthly_payment: Number(data.get('payment')), first_payment_date: String(data.get('date')) })
      if (action.mode === 'settle') await settleLoan(action.loan.id, Number(data.get('amount')), selectedBankId)
      if (action.mode === 'void') await voidLoan(action.loan.id)
      if (action.mode === 'refinance') await refinanceLoan(action.loan.id, { lender: String(data.get('lender')), principal_amount: Number(data.get('principal')), fees: Number(data.get('fees')), annual_rate: Number(data.get('rate')), term_months: Number(data.get('term')), monthly_payment: Number(data.get('payment')), first_payment_date: String(data.get('date')), loan_type: String(data.get('type')), bank_account_code: 1120, bank_account_id: selectedBankId })
      setMessage(t('The operation was completed and posted to the general ledger.'))
      await load()
      setAction(null)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : t('Unable to complete the operation.'))
    }
  }

  return <div className="accounting-view">
    <div className="accounting-view__metrics">
      <article><span>{t('Active loans')}</span><strong>{formatDisplayInteger(active.length, language)}</strong><small>{t('Financing facilities')}</small></article>
      <article><span>{t('Outstanding balance')}</span><strong>{formatMoney(outstanding)}</strong><small>{t('Current principal')}</small></article>
      <article><span>{t('Monthly obligations')}</span><strong>{formatMoney(active.reduce((sum, loan) => sum + Number(loan.monthly_payment), 0))}</strong><small>{t('Included in the debt burden ratio')}</small></article>
    </div>
    <section className="accounting-panel">
      <header><div><h2>{t('Liabilities and loans')}</h2><p>{t('Financing terms and upcoming obligations')}</p></div><Link className="module-page__add" to="/operations/new-loan"><Plus size={14} />{t('New loan')}</Link></header>
      {message && <p className="loan-manager__message">{message}</p>}
      {loading ? <p>{t('Loading loans…')}</p> : !loans.length ? <div className="review-queue__empty"><HandCoins size={22} /><strong>{t('No loans recorded')}</strong><span>{t('Add financing to include it in liabilities and financial health.')}</span></div> : <div className="loan-list">{loans.map((loan) => <article key={loan.id}><div><strong>{loan.name}</strong><small>{loan.lender} · {loanType(loan)}</small></div><div><strong>{formatMoney(Number(loan.outstanding_balance))}</strong><small>{formatMoney(Number(loan.monthly_payment))}/{t('month')}</small></div><em className={`is-${loan.status.toLowerCase()}`}>{status(loan)}</em>{loan.status === 'ACTIVE' && <nav><button onClick={() => setAction({ loan, mode: 'edit' })}><Pencil size={13} />{t('Edit')}</button><button onClick={() => setAction({ loan, mode: 'settle' })}><HandCoins size={13} />{t('Early settlement')}</button><button onClick={() => setAction({ loan, mode: 'refinance' })}><RefreshCcw size={13} />{t('Refinance')}</button><button className="is-danger" onClick={() => setAction({ loan, mode: 'void' })}><Trash2 size={13} />{t('Void')}</button></nav>}</article>)}</div>}
    </section>
    {action && <div className="loan-manager"><form onSubmit={submit}><header><div><small>{t('Manage loan')}</small><h3>{actionTitle}</h3><p>{action.loan.name} · {action.loan.lender}</p></div><button type="button" aria-label={t('Close')} onClick={() => setAction(null)}><X size={17} /></button></header>
      {action.mode === 'edit' && <div className="loan-manager__grid"><label>{t('Name')}<input name="name" required defaultValue={action.loan.name} /></label><label>{t('Lender')}<input name="lender" required defaultValue={action.loan.lender} /></label><label>{t('Annual rate %')}<input name="rate" type="number" step=".01" required defaultValue={action.loan.annual_rate} /></label><label>{t('Term in months')}<input name="term" type="number" required defaultValue={action.loan.term_months} /></label><label>{t('Monthly payment')}<input name="payment" type="number" step=".01" required defaultValue={action.loan.monthly_payment} /></label><label>{t('First payment')}<input name="date" type="date" required defaultValue={action.loan.first_payment_date} /></label></div>}
      {action.mode === 'settle' && <div className="loan-manager__grid"><label>{t('Outstanding balance')}<input disabled value={action.loan.outstanding_balance} /></label><label>{t('Settlement amount')}<input name="amount" type="number" step=".01" required defaultValue={action.loan.outstanding_balance} /></label><p>{t('Any amount above the balance is recorded as a financing cost, while a discount is recorded separately.')}</p></div>}
      {action.mode === 'refinance' && <div className="loan-manager__grid"><label>{t('New lender')}<input name="lender" required /></label><label>{t('New principal')}<input name="principal" type="number" step=".01" required defaultValue={action.loan.outstanding_balance} /></label><label>{t('Fees')}<input name="fees" type="number" step=".01" defaultValue="0" /></label><label>{t('Loan type')}<select name="type" defaultValue={action.loan.loan_type}><option value="SHORT_TERM">{t('Short term')}</option><option value="LONG_TERM">{t('Long term')}</option><option value="MORTGAGE">{t('Mortgage')}</option></select></label><label>{t('Annual rate %')}<input name="rate" type="number" step=".01" required /></label><label>{t('Term in months')}<input name="term" type="number" required /></label><label>{t('Monthly payment')}<input name="payment" type="number" step=".01" required /></label><label>{t('First payment')}<input name="date" type="date" required /></label></div>}
      {action.mode === 'void' && <div className="loan-manager__warning"><Trash2 size={20} /><p><strong>{t('This does not erase the record.')}</strong>{t('A reversing entry will be posted and the loan will remain in the audit trail with a voided status.')}</p></div>}
      <footer><button type="button" onClick={() => setAction(null)}>{t('Cancel')}</button><button className={action.mode === 'void' ? 'is-danger' : ''} type="submit">{t('Review and confirm')}</button></footer>
    </form></div>}
  </div>
}
