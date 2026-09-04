import type { ReactNode } from 'react'

import TradeOperation from './TradeOperation'
import TransferOperation from './TransferOperation'
import IncomeOperation from './IncomeOperation'
import AddCashOperation from './AddCashOperation'
import WithdrawCashOperation from './WithdrawCashOperation'
import LoanOperation from './LoanOperation'
import AddBrokerOperation from './AddBrokerOperation'
import CardPaymentOperation from './CardPaymentOperation'
import JournalOperation from './JournalOperation'
import PropertyPurchaseOperation from './PropertyPurchaseOperation'
import ExpenseOperation from './ExpenseOperation'
import CreditCardAccountOperation from './CreditCardAccountOperation'
import BankAccountOperation from './BankAccountOperation'
import DepositOperation from './DepositOperation'
import BuyOtherAssetOperation from './BuyOtherAssetOperation'
import OpeningCashOperation from './OpeningCashOperation'
import AssetDispositionOperation from './AssetDispositionOperation'
import InheritanceOperation from './InheritanceOperation'
import BankCardOperation from './BankCardOperation'
import PropertyValuationOperation from './PropertyValuationOperation'
import BankOpeningBalanceOperation from './BankOpeningBalanceOperation'

type OperationRenderer = (
  operationId: string,
) => ReactNode

export const operationRenderer: OperationRenderer =
  (operationId) => {
    switch (operationId) {
      case 'trade':
        return <TradeOperation />

      case 'add-broker':
        return <AddBrokerOperation />

      case 'deposit':
        return <DepositOperation />

      case 'transfer':
        return <TransferOperation />

      case 'income':
        return <IncomeOperation />

      case 'add-cash':
        return <AddCashOperation />

      case 'withdraw-cash':
        return <WithdrawCashOperation />

      case 'opening-cash':
        return <OpeningCashOperation />

      case 'inheritance':
        return <InheritanceOperation />

      case 'expense':
        return <ExpenseOperation />

      case 'card-payment':
        return <CardPaymentOperation />

      case 'buy-asset':
        return <BuyOtherAssetOperation />

      case 'sell-asset':
        return <AssetDispositionOperation kind="PROPERTY" />

      case 'break-deposit':
        return <AssetDispositionOperation kind="DEPOSIT" />

      case 'journal-entry':
        return <JournalOperation />

      case 'bank-account':
        return <BankAccountOperation />

      case 'bank-opening-balance':
        return <BankOpeningBalanceOperation />

      case 'credit-card-account':
        return <CreditCardAccountOperation />

      case 'bank-card':
        return <BankCardOperation />

      case 'property':
        return <PropertyPurchaseOperation />

      case 'property-valuation':
        return <PropertyValuationOperation />

      case 'new-loan':
        return <LoanOperation />

      default:
        return <>Operation not implemented.</>
    }
  }
