import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import OperationForm from './OperationForm'
import { withdrawCash } from '../services/withdrawCashService'
import { usePortfolios } from '../hooks/usePortfolios'
import { getBankAccounts, type BankAccount } from '../services/accountingService'
import { useLanguage } from '../context/LanguageContext'

export default function WithdrawCashOperation() {
  const {t,language}=useLanguage()
  const {portfolios,loading,error}=usePortfolios()
  const [portfolioId, setPortfolioId] = useState('')
  const [bankAccounts,setBankAccounts]=useState<BankAccount[]>([])
  const [destinationBankAccountId,setDestinationBankAccountId]=useState('')
  const [amount, setAmount] = useState('')
  const [transactionDate, setTransactionDate] =
    useState('')
  const [description, setDescription] =
    useState(()=>t('Cash withdrawal'))

  const [message, setMessage] = useState('')
  useEffect(()=>{getBankAccounts().then(setBankAccounts).catch(()=>setBankAccounts([]))},[])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    try {
      await withdrawCash({
        portfolio_id: Number(portfolioId),
        destination_bank_account_id: Number(destinationBankAccountId),
        amount: Number(amount),
        transaction_date: transactionDate,
        description,
      })

      setMessage(
        t('Cash withdrawn successfully.'),
      )
    } catch {
      setMessage(t('Unable to withdraw cash.'))
    }
  }

  return (
    <OperationForm
      title={t('Withdraw Cash')}
      onSubmit={handleSubmit}
    >
      <div>
        <label>{t('Portfolio')}</label>

        <select
          value={portfolioId}
          onChange={(event) =>
            setPortfolioId(event.target.value)
          }
        ><option value="">{t('Select Portfolio')}</option>{portfolios.map(portfolio=><option value={portfolio.id} key={portfolio.id}>{portfolio.name} · {t('Cash')} {portfolio.cash_balance.toLocaleString(language==='ar'?'ar-SA':'en-US',{minimumFractionDigits:2})}</option>)}</select>
      </div>

      <div><label>{t('Destination Bank Account')}</label><select value={destinationBankAccountId} onChange={event=>setDestinationBankAccountId(event.target.value)}><option value="">{t('Select Destination Bank Account')}</option>{bankAccounts.map(account=><option value={account.id} key={account.id}>{account.account_name} · {account.currency_code} {Number(account.current_balance).toLocaleString(language==='ar'?'ar-SA':'en-US',{minimumFractionDigits:2})}</option>)}</select></div>

      <div>
        <label>{t('Amount')}</label>

        <input
          type="number"
          value={amount}
          onChange={(event) =>
            setAmount(event.target.value)
          }
        />
      </div>

      <div>
        <label>{t('Transaction Date')}</label>

        <input
          type="datetime-local"
          value={transactionDate}
          onChange={(event) =>
            setTransactionDate(event.target.value)
          }
        />
      </div>

      <div>
        <label>{t('Description')}</label>

        <input
          type="text"
          value={description}
          onChange={(event) =>
            setDescription(event.target.value)
          }
        />
      </div>

      {error&&<p>{error}</p>}
      <button type="submit" disabled={loading||!portfolioId||!destinationBankAccountId||!amount||!transactionDate}>
        {t('Withdraw Brokerage Cash')}
      </button>

      {message && <p>{message}</p>}
    </OperationForm>
  )
}
