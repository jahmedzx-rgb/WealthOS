import type { ElementType } from 'react'

import {
  ArrowLeftRight,
  BookOpen,
  Building2,
  ChartCandlestick,
  CircleMinus,
  CirclePlus,
  CreditCard,
  DollarSign,
  Landmark,
  HandCoins,
  Receipt,
  PackagePlus,
  Wallet,
  Sprout,
  Gift,
} from 'lucide-react'

export type OperationCategory =
  | 'investing'
  | 'accounting'
  | 'assets'
  | 'liabilities'

export type OperationStatus =
  | 'active'
  | 'planned'
  | 'experimental'

export type OperationDefinition = {
  id: string
  title: string
  description: string

  icon: ElementType

  route: string

  category: OperationCategory

  quickAction: boolean

  order: number

  status: OperationStatus
}

export const operationRegistry: Record<
  string,
  OperationDefinition
> = {
  trade: {
    id: 'trade',
    title: 'Trade',
    description:
      'Buy or sell investment securities.',

    icon: ChartCandlestick,

    route: '/operations/trade',

    category: 'investing',

    quickAction: true,

    order: 9,

    status: 'active',
  },

  income: {
    id: 'income',
    title: 'Income',
    description:
      'Record a new income transaction.',

    icon: DollarSign,

    route: '/operations/income',

    category: 'accounting',

    quickAction: true,

    order: 1,

    status: 'active',
  },

  expense: {
    id: 'expense',
    title: 'Expense',
    description:
      'Record a new expense transaction.',

    icon: Receipt,

    route: '/operations/expense',

    category: 'accounting',

    quickAction: true,

    order: 2,

    status: 'active',
  },

  transfer: {
    id: 'transfer',
    title: 'Transfer Funds',
    description:
      'Transfer funds between your accounts.',

    icon: ArrowLeftRight,

    route: '/operations/transfer',

    category: 'accounting',

    quickAction: true,

    order: 3,

    status: 'active',
  },

  'add-broker': {
    id: 'add-broker',
    title: 'Add Broker',
    description:
      'Register a broker for investment trades.',
    icon: Building2,
    route: '/operations/add-broker',
    category: 'investing',
    quickAction: false,
    order: 10,
    status: 'active',
  },

  deposit: {
    id: 'deposit',
    title: 'Add Deposit',
    description: 'Fund a term deposit or income-producing savings product.',
    icon: Sprout,
    route: '/operations/deposit',
    category: 'investing',
    quickAction: false,
    order: 11,
    status: 'active',
  },

  'add-cash': {
    id: 'add-cash',
    title: 'Fund Brokerage Cash',
    description: 'Move cash from your bank account into brokerage cash.',
    icon: CirclePlus,
    route: '/operations/add-cash',
    category: 'accounting',
    quickAction: true,
    order: 4,
    status: 'active',
  },

  'withdraw-cash': {
    id: 'withdraw-cash',
    title: 'Withdraw Brokerage Cash',
    description: 'Move available brokerage cash back to your bank account.',
    icon: CircleMinus,
    route: '/operations/withdraw-cash',
    category: 'accounting',
    quickAction: true,
    order: 5,
    status: 'active',
  },

  'opening-cash': {
    id: 'opening-cash',
    title: 'Cash On Hand Asset',
    description: 'Set up cash owned before WealthOS or post a documented opening-balance correction.',
    icon: Wallet,
    route: '/operations/opening-cash',
    category: 'assets',
    quickAction: false,
    order: 5.5,
    status: 'active',
  },

  inheritance: {
    id: 'inheritance',
    title: 'Record Inheritance',
    description: 'Record inherited cash, property, investments, or other assets without treating them as operating income.',
    icon: Gift,
    route: '/operations/inheritance',
    category: 'assets',
    quickAction: false,
    order: 5.6,
    status: 'active',
  },

  'card-payment': {
    id: 'card-payment',
    title: 'Credit Card Payment',
    description:
      'Pay a credit card balance.',

    icon: CreditCard,

    route: '/operations/card-payment',

    category: 'liabilities',

    quickAction: true,

    order: 6,

    status: 'active',
  },

  'buy-asset': {
    id: 'buy-asset',
    title: 'Buy Other Asset',
    description:
      'Acquire a long-term asset.',

    icon: PackagePlus,

    route: '/operations/buy-asset',

    category: 'assets',

    quickAction: true,

    order: 7,

    status: 'active',
  },

  'sell-asset': {
    id: 'sell-asset',
    title: 'Sell Asset',
    description:
      'Dispose of a long-term asset.',

    icon: Wallet,

    route: '/operations/sell-asset',

    category: 'assets',

    quickAction: true,

    order: 8,

    status: 'active',
  },

  'break-deposit': {
    id: 'break-deposit',
    title: 'Break Deposit',
    description: 'Close a deposit and post the actual settlement received.',
    icon: Sprout,
    route: '/operations/break-deposit',
    category: 'assets',
    quickAction: false,
    order: 9,
    status: 'active',
  },

  'journal-entry': {
    id: 'journal-entry',
    title: 'Manual Journal',

    description:
      'Create an advanced journal entry.',

    icon: BookOpen,

    route: '/operations/journal-entry',

    category: 'accounting',

    quickAction: false,

    order: 100,

    status: 'active',
  },

  'bank-account': {
    id: 'bank-account',
    title: 'Add Bank Account',
    description:
      'Connect or create a bank account.',
    icon: Landmark,
    route: '/operations/bank-account',
    category: 'accounting',
    quickAction: false,
    order: 110,
    status: 'active',
  },
  'bank-opening-balance': { id:'bank-opening-balance', title:'Bank Opening Balance', description:'Add or correct the documented opening balance without changing later transactions.', icon:Landmark, route:'/operations/bank-opening-balance', category:'accounting', quickAction:false, order:110.5, status:'active' },

  'credit-card-account': { id:'credit-card-account', title:'Add Credit Card', description:'Define a credit card detected in an imported operation.', icon:CreditCard, route:'/operations/credit-card-account', category:'liabilities', quickAction:false, order:111, status:'active' },
  'bank-card': { id:'bank-card', title:'Add Bank Debit Card', description:'Link a debit card to its bank account.', icon:CreditCard, route:'/operations/bank-card', category:'accounting', quickAction:false, order:112, status:'active' },
  'property': { id:'property', title:'Buy Property', description:'Purchase and post a property to the real estate ledger.', icon:Landmark, route:'/operations/property', category:'assets', quickAction:false, order:113, status:'active' },
  'property-valuation': { id:'property-valuation', title:'Add Property Valuation', description:'Update the current market value of a property.', icon:Landmark, route:'/operations/property-valuation', category:'assets', quickAction:false, order:114, status:'active' },
  'new-loan': { id:'new-loan', title:'New Loan', description:'Record financing, received funds, fees, and repayment terms.', icon:HandCoins, route:'/operations/new-loan', category:'liabilities', quickAction:false, order:115, status:'active' },
  'manage-loans': { id:'manage-loans', title:'Manage Loans', description:'Edit, settle, refinance, or reverse an existing loan.', icon:HandCoins, route:'/accounting?tab=loans', category:'liabilities', quickAction:false, order:116, status:'active' },
}
