import { Link } from 'react-router-dom'

import Card from '../ui/Card'
import type { PortfolioPosition } from '../../types/portfolio'
import { useCurrency, type Currency } from '../../context/CurrencyContext'
import FormattedMoney from '../ui/FormattedMoney'
import type { BalanceItem, Deposit } from '../../services/accountingService'
import './WealthAllocationOverview.css'
import { formatDisplayPercent } from '../../utils/localeFormat'
import { useLanguage } from '../../context/LanguageContext'

type Props = {
  allocation: Record<string, number>
  positions: PortfolioPosition[]
  totalValue: number
  portfolioCurrency?: Currency
  assetBreakdown?: BalanceItem[]
  deposits?: Deposit[]
  compact?: boolean
  showLink?: boolean
  realEstateReturn?: number
}

const categoryNames: Record<string, string> = {
  STOCK: 'Stocks',
  ETF: 'ETFs',
  FUND: 'Funds',
  BOND: 'Bonds & Sukuk',
  REIT: 'REITs',
  DEPOSIT: 'Deposits',
  PRIVATE_CREDIT: 'Private Credit',
  CASH: 'Cash',
  REAL_ESTATE: 'Real Estate',
  SAVINGS: 'Savings & Lending',
  OTHER_ASSETS: 'Other Assets',
}

const colors = ['#243f68', '#5274a4', '#16855a', '#b68a26', '#8a94a3', '#725d91']

export default function WealthAllocationOverview({ allocation, positions, totalValue, assetBreakdown=[], deposits=[], compact=false, showLink=true, realEstateReturn=0 }: Props) {
  const { formatMoney } = useCurrency()
  const { t } = useLanguage()
  const normalizedAllocation = new Map<string,number>()
  for (const [type, weight] of Object.entries(allocation)) {
    const assetClass = type === 'REIT' ? 'STOCK' : type
    normalizedAllocation.set(assetClass, (normalizedAllocation.get(assetClass) ?? 0) + weight)
  }
  const marketCategories = [...normalizedAllocation.entries()]
    .map(([type, weight], index) => {
      const categoryPositions = positions.filter((position) => (position.security_type === 'REIT' ? 'STOCK' : position.security_type) === type)
      const totalCost = categoryPositions.reduce((sum, position) => sum + position.total_cost, 0)
      const unrealizedProfit = categoryPositions.reduce((sum, position) => sum + position.unrealized_pl, 0)
      return {
        type,
        label: t(categoryNames[type] ?? type.replaceAll('_', ' ')),
        weight: weight * 100,
        value: totalValue * weight,
        returnPercentage: totalCost ? (unrealizedProfit / totalCost) * 100 : 0,
        color: colors[index % colors.length],
      }
    })
  const ledgerGroups=new Map<string,number>()
  for(const asset of assetBreakdown){
    if(asset.code>=1310&&asset.code<=1390)continue
    const type=asset.code===1160?'DEPOSIT':asset.code===1170?'SAVINGS':asset.code===1210?'REAL_ESTATE':asset.code>=1110&&asset.code<=1150?'CASH':'OTHER_ASSETS'
    ledgerGroups.set(type,(ledgerGroups.get(type)??0)+asset.balance)
  }
  const depositBalance=deposits.reduce((sum,item)=>sum+item.current_balance,0)
  const depositAnnualReturn=depositBalance?deposits.reduce((sum,item)=>sum+item.current_balance*item.annual_return_rate,0)/depositBalance:0
  const ledgerCategories=[...ledgerGroups.entries()].filter(([,value])=>value>0).map(([type,value],index)=>({type,label:t(categoryNames[type]??type.replaceAll('_',' ')),value,returnPercentage:type==='DEPOSIT'?depositAnnualReturn:type==='REAL_ESTATE'?realEstateReturn:0,color:colors[(marketCategories.length+index)%colors.length],weight:0}))
  const mergedCategories=new Map<string,(typeof marketCategories)[number]>()
  for(const item of [...marketCategories,...ledgerCategories]){
    const existing=mergedCategories.get(item.type)
    mergedCategories.set(item.type,existing?{...existing,value:existing.value+item.value}:item)
  }
  const totalAssets=[...mergedCategories.values()].reduce((sum,item)=>sum+item.value,0)
  const categories=[...mergedCategories.values()]
    .map(item=>({...item,weight:totalAssets?item.value/totalAssets*100:0}))
    .sort((a, b) => b.weight - a.weight)

  return (
    <Card
      className="wealth-allocation"
      title={t('Wealth Allocation')}
      action={showLink?<Link className="wealth-allocation__link" to="/investing">{t('View all assets')} →</Link>:undefined}
    >
      <div className="wealth-allocation__grid">
        <div>
          <div className="wealth-allocation__total">
            <span>{t('Total assets by class')}</span>
            <strong><FormattedMoney value={formatMoney(totalAssets, 'SAR')}/></strong>
          </div>

          <div className="wealth-allocation__bar" role="img" aria-label="Live investment allocation by security type">
            {categories.map((item) => <span key={item.type} style={{ width: `${item.weight}%`, background: item.color }} />)}
          </div>

          <div className="wealth-allocation__legend">
            {categories.map((item) => (
              <div key={item.type}>
                <span><i style={{ background: item.color }} />{item.label}</span>
                <strong style={{ color: item.color }}>{formatDisplayPercent(item.weight)}</strong>
              </div>
            ))}
          </div>
        </div>

        {!compact&&<div className="wealth-allocation__classes">
          <div className="wealth-allocation__table-head"><span>{t('Class')}</span><span>{t('Value')}</span><span>{t('Return')}</span><span>{t('Weight')}</span></div>
          {categories.map((item) => {
            return <div key={item.type}>
              <strong>{item.label}</strong>
              <span><FormattedMoney value={formatMoney(item.value, 'SAR')}/></span>
              <span className={item.returnPercentage >= 0 ? 'is-positive' : 'is-negative'}>{marketCategories.some(category=>category.type===item.type)||item.type==='DEPOSIT'&&depositBalance>0||item.type==='REAL_ESTATE'?<>{item.returnPercentage >= 0 ? '+' : ''}{formatDisplayPercent(item.returnPercentage)}</>:'—'}</span>
              <span>{formatDisplayPercent(item.weight)}</span>
            </div>
          })}
        </div>}
      </div>
    </Card>
  )
}
