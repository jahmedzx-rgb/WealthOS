import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import OperationForm from './OperationForm'
import { addCash } from '../services/accountingService'
import { usePortfolios } from '../hooks/usePortfolios'
import { useSearchParams } from 'react-router-dom'
import { useFinancialSummary } from '../hooks/useFinancialSummary'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'

const amountInput=(value:string)=>{const cleaned=value.replace(/[^\d.]/g,'');const[whole='',...decimal]=cleaned.split('.');const grouped=whole.replace(/\B(?=(\d{3})+(?!\d))/g,',');return cleaned.includes('.')?`${grouped}.${decimal.join('').slice(0,2)}`:grouped}
const amountValue=(value:string)=>value.replace(/,/g,'').replace(/[^\d.]/g,'')
const localNow=()=>new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)

export default function AddCashOperation() {
  const[searchParams]=useSearchParams()
  const financial=useFinancialSummary()
  const{formatMoney}=useCurrency()
  const{t,language}=useLanguage()
  const {portfolios,loading,error}=usePortfolios()
  const [portfolioId, setPortfolioId] = useState(()=>searchParams.get('portfolio')??'')
  const[sourceBankAccountId,setSourceBankAccountId]=useState('')
  const [amount, setAmount] = useState('')
  const [transactionDate, setTransactionDate] =
    useState(localNow)
  const [description, setDescription] =
    useState(()=>t('Cash deposit'))
  const selectedPortfolio=portfolios.find(item=>item.id===Number(portfolioId))
  const matchingBankAccounts=(financial.data?.bank_accounts??[]).filter(account=>!selectedPortfolio||account.currency_code===selectedPortfolio.base_currency_code)

  const [message, setMessage] = useState('')
  useEffect(()=>{const accounts=matchingBankAccounts;if(!accounts.length){if(sourceBankAccountId)queueMicrotask(()=>setSourceBankAccountId(''));return}const required=Number(amount||0);const current=accounts.find(item=>String(item.id)===sourceBankAccountId);if(current&&current.current_balance>=required)return;const eligible=accounts.filter(item=>item.current_balance>=required);const smart=eligible.find(item=>item.is_primary)??eligible.sort((a,b)=>b.current_balance-a.current_balance)[0]??accounts.find(item=>item.is_primary)??[...accounts].sort((a,b)=>b.current_balance-a.current_balance)[0];if(smart)queueMicrotask(()=>setSourceBankAccountId(String(smart.id)))},[amount,matchingBankAccounts,sourceBankAccountId])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    try {
      await addCash({
        portfolio_id: Number(portfolioId),
        source_bank_account_id: Number(sourceBankAccountId),
        amount: Number(amount),
        transaction_date: transactionDate,
        description,
      })

      setMessage(t('Cash added successfully.'))
    } catch {
      setMessage(t('Unable to add cash.'))
    }
  }

  return (
    <OperationForm
      title={t('Add Cash')}
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

      <div className="add-cash-operation__funding-row">
        <div>
          <label>{t('Funding Bank Account')} <small>{t('Auto-selected')}</small></label>
          <select value={sourceBankAccountId} onChange={event=>setSourceBankAccountId(event.target.value)}>
            <option value="">{t('Select Source Account')}</option>
            {matchingBankAccounts.map(account=><option value={account.id} key={account.id}>{account.is_primary?`${t('Primary')} · `:''}{account.account_name} · {account.bank_name} · {formatMoney(account.current_balance,account.currency_code as Parameters<typeof formatMoney>[1])}</option>)}
          </select>
          {selectedPortfolio&&!matchingBankAccounts.length?<small>{t('No bank account is available in')} {selectedPortfolio.base_currency_code}.</small>:null}
        </div>

        <div>
          <label>{t('Amount')}</label>
          <input
            type="text"
            inputMode="decimal"
            value={amountInput(amount)}
            onChange={(event) =>
              setAmount(amountValue(event.target.value))
            }
            placeholder="0.00"
          />
        </div>
      </div>

      <div className="add-cash-operation__details-row">
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
      </div>

      {error&&<p>{error}</p>}
      <button type="submit" disabled={loading||financial.loading||!portfolioId||!sourceBankAccountId||!amount||!transactionDate}>
        {t('Fund Brokerage Cash')}
      </button>

      {message && <p>{message}</p>}
    </OperationForm>
  )
}
