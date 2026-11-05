import { lazy, type ReactNode } from 'react'

const TradeOperation=lazy(()=>import('./TradeOperation'))
const TransferOperation=lazy(()=>import('./TransferOperation'))
const IncomeOperation=lazy(()=>import('./IncomeOperation'))
const AddCashOperation=lazy(()=>import('./AddCashOperation'))
const WithdrawCashOperation=lazy(()=>import('./WithdrawCashOperation'))
const LoanOperation=lazy(()=>import('./LoanOperation'))
const AddBrokerOperation=lazy(()=>import('./AddBrokerOperation'))
const AddInvestmentPlatformOperation=lazy(()=>import('./AddInvestmentPlatformOperation'))
const CardPaymentOperation=lazy(()=>import('./CardPaymentOperation'))
const JournalOperation=lazy(()=>import('./JournalOperation'))
const PropertyPurchaseOperation=lazy(()=>import('./PropertyPurchaseOperation'))
const ExpenseOperation=lazy(()=>import('./ExpenseOperation'))
const CreditCardAccountOperation=lazy(()=>import('./CreditCardAccountOperation'))
const BankAccountOperation=lazy(()=>import('./BankAccountOperation'))
const DepositOperation=lazy(()=>import('./DepositOperation'))
const BuyOtherAssetOperation=lazy(()=>import('./BuyOtherAssetOperation'))
const OpeningCashOperation=lazy(()=>import('./OpeningCashOperation'))
const AssetDispositionOperation=lazy(()=>import('./AssetDispositionOperation'))
const InheritanceOperation=lazy(()=>import('./InheritanceOperation'))
const BankCardOperation=lazy(()=>import('./BankCardOperation'))
const PropertyValuationOperation=lazy(()=>import('./PropertyValuationOperation'))
const BankOpeningBalanceOperation=lazy(()=>import('./BankOpeningBalanceOperation'))
const OpeningPropertyOperation=lazy(()=>import('./OpeningPropertyOperation'))
const OpeningPortfolioOperation=lazy(()=>import('./OpeningPortfolioOperation'))

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

      case 'add-investment-platform':
        return <AddInvestmentPlatformOperation />

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

      case 'opening-property':
        return <OpeningPropertyOperation />

      case 'opening-portfolio':
        return <OpeningPortfolioOperation />

      case 'property-valuation':
        return <PropertyValuationOperation />

      case 'new-loan':
        return <LoanOperation />

      default:
        return <>Operation not implemented.</>
    }
  }
