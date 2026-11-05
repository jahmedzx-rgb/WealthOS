import { useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { ChevronDown, ChevronUp, Settings2 } from 'lucide-react'

import Card from '../ui/Card'
import Table from '../ui/Table'
import FormattedMoney from '../ui/FormattedMoney'
import { marketName } from '../../utils/marketPriceFreshness'

import './PositionsTable.css'
import { formatDisplayPercent } from '../../utils/localeFormat'

import type { PortfolioPosition } from '../../types/portfolio'
import { useCurrency, type Currency } from '../../context/CurrencyContext'
import { marketPriceFreshness } from '../../utils/marketPriceFreshness'
import FairValueEditor from '../investing/FairValueEditor'
import { useLanguage } from '../../context/LanguageContext'
import { securityDisplayName, securityDisplaySymbol } from '../../utils/securityName'
import BrokerLogo from '../ui/BrokerLogo'

type Props = {
  portfolioId: number | 'consolidated'
  positions: PositionRow[]
  title?: string
  subtitle?: string
  brokerName?: string | null
  historical?: boolean
  emptyMessage?: string
}

type PositionRow = Omit<PortfolioPosition, 'market_price' | 'market_price_date' | 'market_value' | 'unrealized_pl' | 'market_value_base' | 'unrealized_pl_base'> & {
  market_price: number | null
  market_price_date: string | null
  market_value: number | null
  unrealized_pl: number | null
  market_value_base: number | null
  unrealized_pl_base: number | null
}

type Column='quantity'|'price'|'costPrice'|'cost'|'market'|'fair'|'pl'|'dividend'|'distributionFrequency'|'yieldCost'|'weight'
const columnOptions:Array<{id:Column;label:string}>=[
  {id:'quantity',label:'Quantity'},{id:'price',label:'Price'},{id:'costPrice',label:'Cost Price'},{id:'cost',label:'Cost Basis'},
  {id:'market',label:'Market Value'},{id:'fair',label:'Fair Value'},
  {id:'pl',label:'Unrealized P/L'},{id:'dividend',label:'Dividend Yield'},{id:'distributionFrequency',label:'Distribution Frequency'},{id:'yieldCost',label:'Yield on Cost'},{id:'weight',label:'Weight'},
]
const defaultColumns:Column[]=['quantity','price','cost','fair','pl','dividend','yieldCost','weight']
const maxOptionalColumns=8
const annualFrequency:Record<string,number>={WEEKLY:52,MONTHLY:12,QUARTERLY:4,SEMI_ANNUAL:2,SEMIANNUAL:2,ANNUAL:1,YEARLY:1}
const distributionFrequencyLabel:Record<string,string>={WEEKLY:'Weekly',MONTHLY:'Monthly',QUARTERLY:'Quarterly',SEMI_ANNUAL:'Semi-Annual',SEMIANNUAL:'Semi-Annual',ANNUAL:'Annual',YEARLY:'Annual',AT_MATURITY:'At Maturity',IRREGULAR:'Irregular'}

export default function PositionsTable({
  portfolioId,
  positions,
  title,
  subtitle,
  brokerName,
  historical = false,
  emptyMessage,
}: Props) {
  const navigate = useNavigate()
  const { formatMoney } = useCurrency()
  const { t, language } = useLanguage()
  const [designOpen,setDesignOpen]=useState(false)
  const [collapsed,setCollapsed]=useState(false)
  const [columns,setColumns]=useState<Column[]>(()=>{try{const saved=JSON.parse(localStorage.getItem('wealthos.positions.columns.v5')??'null');return Array.isArray(saved)?saved.slice(0,maxOptionalColumns):defaultColumns}catch{return defaultColumns}})
  function toggleColumn(column:Column){
    const next=columns.includes(column)
      ? columns.filter(item=>item!==column)
      : columns.length<maxOptionalColumns?[...columns,column]:columns
    if(next===columns)return
    setColumns(next)
    localStorage.setItem('wealthos.positions.columns.v5',JSON.stringify(next))
    window.dispatchEvent(new CustomEvent('wealthos:positions-columns',{detail:next}))
  }
  const visible=(column:Column)=>columns.includes(column)
  useEffect(()=>{const sync=(event:Event)=>setColumns((event as CustomEvent<Column[]>).detail);window.addEventListener('wealthos:positions-columns',sync);return()=>window.removeEventListener('wealthos:positions-columns',sync)},[])

  return (
    <Card title={brokerName?undefined:title??t('Positions')} titleNode={brokerName?<span className="positions-table__broker-title"><BrokerLogo name={brokerName}/><span className="positions-table__broker-copy"><span>{title}</span>{subtitle?<small>{subtitle}</small>:null}</span></span>:undefined} subtitle={brokerName?undefined:subtitle} className={`positions-table${collapsed?' is-collapsed':''}`} action={<div className="positions-table__actions"><button className="positions-table__collapse" type="button" onClick={()=>setCollapsed(value=>!value)} aria-expanded={!collapsed} aria-label={t(collapsed?'Expand portfolio':'Collapse portfolio')} title={t(collapsed?'Expand portfolio':'Collapse portfolio')}>{collapsed?<ChevronDown size={16}/>:<ChevronUp size={16}/>}</button><div className="positions-table__design"><button type="button" onClick={()=>setDesignOpen(value=>!value)}><Settings2 size={14}/>{t('View Design')}</button>{designOpen?<div>{columnOptions.map(column=>{const unavailable=!visible(column.id)&&columns.length>=maxOptionalColumns;return <label key={column.id} className={unavailable?'positions-table__design-disabled':undefined}><input type="checkbox" checked={visible(column.id)} disabled={unavailable} onChange={()=>toggleColumn(column.id)}/><span>{t(column.label)}</span></label>})}<small>{t('Display up to 9 columns')}</small></div>:null}</div></div>}>
      {!collapsed?<Table>
        <thead>
          <tr>
            <th>{t('Symbol')}</th>
            {visible('quantity')?<th className="positions-table__number positions-table__quantity">{t('Quantity')}</th>:null}
            {visible('price')?<th className="positions-table__number positions-table__price-column">{t('Price')}</th>:null}
            {visible('costPrice')?<th className="positions-table__number positions-table__cost-price">{t('Cost Price')}</th>:null}
            {visible('cost')?<th className="positions-table__number positions-table__cost-basis">{t('Cost Basis')}</th>:null}
            {visible('market')?<th className="positions-table__number positions-table__market-value">{t('Market Value')}</th>:null}
            {visible('fair')&&!historical?<th className="positions-table__number positions-table__fair-value">{t('Fair Value')}</th>:null}
            {visible('pl')?<th className="positions-table__number positions-table__unrealized">{t('Unrealized P/L')}</th>:null}
            {visible('dividend')?<th className="positions-table__number positions-table__dividend-yield">{t('Dividend Yield')}</th>:null}
            {visible('distributionFrequency')?<th className="positions-table__number positions-table__distribution-frequency">{t('Distribution Frequency')}</th>:null}
            {visible('yieldCost')?<th className="positions-table__number positions-table__yield-on-cost">{t('Yield on Cost')}</th>:null}
            {visible('weight')?<th className="positions-table__number positions-table__weight">{t('Weight')}</th>:null}
          </tr>
        </thead>

        <tbody>
          {positions.map((position) => (
            <tr
              key={position.security_id}
              onClick={() => !historical &&
                navigate(
                  `/portfolios/${position.portfolio_id ?? portfolioId}/positions/${position.security_id}`
                )
              }
              style={{ cursor: historical ? 'default' : 'pointer' }}
            >
              <td className="positions-table__symbol">
                {securityDisplaySymbol(position.symbol)}
                <strong>{securityDisplayName(position,language)}</strong>
                <small>{position.exchange ? t(marketName(position.exchange)) : null}</small>
              </td>

              {visible('quantity')?<td className="positions-table__number positions-table__quantity">
                {position.quantity}
              </td>:null}

              {visible('price')?<td className="positions-table__number positions-table__price positions-table__price-column">
                {position.market_price==null?'—':<FormattedMoney value={formatMoney(position.market_price, position.currency_code as Parameters<typeof formatMoney>[1])}/>}
                <small>{position.market_price_date?t(marketPriceFreshness(position.market_price_date,undefined,position.exchange).status):t('No historical close available')}</small>
              </td>:null}

              {visible('costPrice')?<td className="positions-table__number positions-table__cost-price"><FormattedMoney value={formatMoney(position.average_cost,position.currency_code as Parameters<typeof formatMoney>[1])}/></td>:null}

              {visible('cost')?<td className="positions-table__number positions-table__cost-basis"><FormattedMoney value={formatMoney(position.total_cost,position.currency_code as Parameters<typeof formatMoney>[1])}/></td>:null}

              {visible('market')?<td className="positions-table__number positions-table__market-value">
                {position.market_value==null?'—':<FormattedMoney value={formatMoney(position.market_value, position.currency_code as Parameters<typeof formatMoney>[1])}/>}
              </td>:null}

              {visible('fair')&&!historical?<td className="positions-table__number positions-table__fair-value" onClick={event=>event.stopPropagation()}><FairValueEditor portfolioId={position.portfolio_id!} securityId={position.security_id} value={position.fair_value} currency={position.currency_code as Currency}/></td>:null}

              {visible('pl')?<td
                className={
                  (position.unrealized_pl??0) >= 0
                    ? 'positions-table__pl positions-table__pl--positive positions-table__unrealized'
                    : 'positions-table__pl positions-table__pl--negative positions-table__unrealized'
                }
              >
                {position.unrealized_pl==null?'—':<FormattedMoney value={formatMoney(position.unrealized_pl, position.currency_code as Parameters<typeof formatMoney>[1])}/>}
              </td>:null}

              {visible('dividend')?<td className="positions-table__number positions-table__dividend-yield">{position.expected_distribution_amount!=null&&(position.market_value??0)>0&&position.distribution_frequency&&annualFrequency[position.distribution_frequency]?formatDisplayPercent(position.expected_distribution_amount*annualFrequency[position.distribution_frequency]!/(position.market_value??1)*100,2):'—'}</td>:null}

              {visible('distributionFrequency')?<td className="positions-table__number positions-table__distribution-frequency">{(()=>{const frequency=position.distribution_frequency;return frequency?t(distributionFrequencyLabel[frequency]??frequency.replaceAll('_',' ')):'—'})()}</td>:null}

              {visible('yieldCost')?<td className="positions-table__number positions-table__yield-on-cost">{position.expected_distribution_amount!=null&&position.total_cost>0&&position.distribution_frequency&&annualFrequency[position.distribution_frequency]?formatDisplayPercent(position.expected_distribution_amount*annualFrequency[position.distribution_frequency]/position.total_cost*100,2):'—'}</td>:null}

              {visible('weight')?<td className="positions-table__number positions-table__weight">
                {formatDisplayPercent(position.weight * 100, 2)}
              </td>:null}
            </tr>
          ))}
          {positions.length===0&&emptyMessage?<tr><td colSpan={1+columns.filter(column=>column!=='fair'||!historical).length}>{emptyMessage}</td></tr>:null}
        </tbody>
      </Table>:null}
    </Card>
  )
}
