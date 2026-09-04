import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'

import OperationForm from './OperationForm'
import { transfer } from '../services/transferService'
import { usePostingAccounts } from '../hooks/usePostingAccounts'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { getBankAccounts, type BankAccount } from '../services/accountingService'
import { useLanguage } from '../context/LanguageContext'

export default function TransferOperation() {
  const {t,language}=useLanguage()
  const imported=useImportedOperationDraft()
  const {accounts,loading,error}=usePostingAccounts()
  const cashAccounts=accounts.filter(account=>account.is_cash_account)
  const [fromAccountCode, setFromAccountCode] =
    useState('')
  const [toAccountCode, setToAccountCode] =
    useState('')
  const [bankAccounts,setBankAccounts]=useState<BankAccount[]>([])
  const [fromBankAccountId,setFromBankAccountId]=useState('')
  const [toBankAccountId,setToBankAccountId]=useState('')
  const [amount, setAmount] = useState(imported.draft?.amount==null?'':String(Math.abs(imported.draft.amount)))
  const [transactionDate, setTransactionDate] =
    useState(toLocalDateTime(imported.draft?.transaction_date))
  const [description, setDescription] =
    useState(imported.draft?.description||t('Funds transfer'))

  const [message, setMessage] = useState('')
  useEffect(()=>{getBankAccounts().then(setBankAccounts).catch(()=>setBankAccounts([]))},[])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    try {
      const result=await transfer({
        from_account_code: Number(fromAccountCode),
        to_account_code: Number(toAccountCode),
        from_bank_account_id: fromAccountCode==='1120'?Number(fromBankAccountId):undefined,
        to_bank_account_id: toAccountCode==='1120'?Number(toBankAccountId):undefined,
        amount: Number(amount),
        transaction_date: transactionDate,
        description,
      })

      await imported.confirm(postingReference(result,'transfer'))

      setMessage(t('Transfer completed successfully.'))
    } catch {
      setMessage(t('Unable to complete the transfer.'))
    }
  }

  return (
    <OperationForm
      title={t('Transfer Funds')}
      onSubmit={handleSubmit}
    >
      <div>
        <label>{t('From Account')}</label>

        <select
          value={fromAccountCode}
          onChange={(event) =>
            setFromAccountCode(event.target.value)
          }
        ><option value="">{t('Select Source Account')}</option>{cashAccounts.map(account=><option value={account.code} key={account.code}>{account.name}</option>)}</select>
      </div>

      {fromAccountCode==='1120'&&<div><label>{t('Source Bank Account')}</label><select value={fromBankAccountId} onChange={event=>setFromBankAccountId(event.target.value)}><option value="">{t('Select Source Bank Account')}</option>{bankAccounts.map(account=><option value={account.id} key={account.id}>{account.account_name} · {account.currency_code} {Number(account.current_balance).toLocaleString(language==='ar'?'ar-SA':'en-US',{minimumFractionDigits:2})}</option>)}</select></div>}

      <div>
        <label>{t('To Account')}</label>

        <select
          value={toAccountCode}
          onChange={(event) =>
            setToAccountCode(event.target.value)
          }
        ><option value="">{t('Select Destination Account')}</option>{cashAccounts.filter(account=>String(account.code)!==fromAccountCode||account.code===1120).map(account=><option value={account.code} key={account.code}>{account.name}</option>)}</select>
      </div>

      {toAccountCode==='1120'&&<div><label>{t('Destination Bank Account')}</label><select value={toBankAccountId} onChange={event=>setToBankAccountId(event.target.value)}><option value="">{t('Select Destination Bank Account')}</option>{bankAccounts.filter(account=>String(account.id)!==fromBankAccountId).map(account=><option value={account.id} key={account.id}>{account.account_name} · {account.currency_code} {Number(account.current_balance).toLocaleString(language==='ar'?'ar-SA':'en-US',{minimumFractionDigits:2})}</option>)}</select></div>}

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
      <button type="submit" disabled={loading||!fromAccountCode||!toAccountCode||!amount||!transactionDate||(fromAccountCode==='1120'&&!fromBankAccountId)||(toAccountCode==='1120'&&!toBankAccountId)}>
        {t('Transfer')}
      </button>

      {message && <p>{message}</p>}
    </OperationForm>
  )
}
