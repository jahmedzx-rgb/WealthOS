/* eslint-disable react-hooks/set-state-in-effect */
import {
  useEffect,
  useState,
} from 'react'
import { Link, useSearchParams } from 'react-router-dom'

import type { FormEvent } from 'react'

import LookupSelect from '../components/LookupSelect'
import MarketSecurityLookup from '../components/MarketSecurityLookup'
import { useBrokers } from '../hooks/useBrokers'
import { usePortfolios } from '../hooks/usePortfolios'
import { useSecurities } from '../hooks/useSecurities'
import { createTrade } from '../services/tradeService'
import { createPortfolio } from '../services/portfolioService'
import { getNextDistribution, type DistributionPreview } from '../services/securityService'
import OperationForm from './OperationForm'
import './TradeOperation.css'
import './TradeOperationEnhancements.css'
import { postingReference, toLocalDateTime, useImportedOperationDraft } from '../hooks/useImportedOperationDraft'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayNumber, formatDisplayPercent } from '../utils/localeFormat'

export default function TradeOperation() {
  const { t, language } = useLanguage()
  const imported=useImportedOperationDraft()
  const [searchParams] = useSearchParams()
  const {
    portfolios,
    loading,
    error,
    refresh: refreshPortfolios,
  } = usePortfolios()

  const {
    brokers,
    loading: brokersLoading,
    error: brokersError,
  } = useBrokers()

  const {
    securities,
    loading: securitiesLoading,
    error: securitiesError,
    refresh: refreshSecurities,
  } = useSecurities()

  const [portfolioId, setPortfolioId] =
    useState('')

  const [brokerId, setBrokerId] =
    useState('')

  const [securityId, setSecurityId] =
    useState('')
  const [side,setSide]=useState<'BUY'|'SELL'>(()=>searchParams.get('side')==='SELL'?'SELL':'BUY')

  const [quantity, setQuantity] =
    useState('')

  const [price, setPrice] =
    useState('')
  const [priceIncludesFees,setPriceIncludesFees]=useState(false)

  const [tradeDate, setTradeDate] =
    useState('')
  const [distributionDate,setDistributionDate]=useState('')
  const [expectedDistribution,setExpectedDistribution]=useState('')
  const [fairValue,setFairValue]=useState('')
  const [distributionPreview,setDistributionPreview]=useState<DistributionPreview|null>(null)
  const [distributionLoading,setDistributionLoading]=useState(false)
  const [distributionAuto,setDistributionAuto]=useState(false)

  const [message, setMessage] =
    useState('')

  const [isSubmitting, setIsSubmitting] =
    useState(false)
  const [newPortfolioName,setNewPortfolioName]=useState('')
  const [newPortfolioNumber,setNewPortfolioNumber]=useState('')
  const [creatingPortfolio,setCreatingPortfolio]=useState(false)
  const selectedBroker=brokers.find(item=>item.id===Number(brokerId))
  const enteredTradeValue=Number(quantity||0)*Number(price||0)
  const feeRate=Number(selectedBroker?.commission_rate??0)/100
  const vatRate=Number(selectedBroker?.commission_tax_rate??0)/100
  const selectedSecurity=securities.find(item=>item.id===Number(securityId))
  const taxableFeeRate=selectedSecurity?.currency_code==='SAR'?Math.max(feeRate-.0005,0):feeRate
  const combinedFeeRate=feeRate+taxableFeeRate*vatRate
  const netTradeValue=priceIncludesFees&&combinedFeeRate>0?enteredTradeValue/(1+combinedFeeRate):enteredTradeValue
  const effectiveUnitPrice=Number(quantity)>0?netTradeValue/Number(quantity):Number(price||0)
  const roundMoney=(value:number)=>Math.round((value+Number.EPSILON)*100)/100
  const baseCommission=roundMoney(netTradeValue*feeRate)
  const commissionTax=roundMoney(netTradeValue*taxableFeeRate*vatRate)
  const calculatedCommission=baseCommission+commissionTax
  const commission=quantity&&price&&selectedBroker?.commission_rate!=null&&selectedBroker?.commission_tax_rate!=null?calculatedCommission.toFixed(2):''
  const totalValue=priceIncludesFees?enteredTradeValue:netTradeValue+calculatedCommission
  const selectedPortfolio=portfolios.find(item=>item.id===Number(portfolioId))
  const requiredCash=totalValue
  const insufficientCash=side==='BUY'&&Boolean(portfolioId)&&requiredCash>(selectedPortfolio?.cash_balance??0)
  useEffect(()=>{if(!securityId){setDistributionPreview(null);setDistributionAuto(false);return}let active=true;setDistributionLoading(true);getNextDistribution(Number(securityId)).then(result=>{if(!active)return;setDistributionPreview(result);if(result.available){if(result.date_kind==='payment'&&result.distribution_date)setDistributionDate(result.distribution_date);setDistributionAuto(true)}}).catch(()=>{if(active)setDistributionPreview({available:false,sources_checked:[]})}).finally(()=>{if(active)setDistributionLoading(false)});return()=>{active=false}},[securityId])
  useEffect(()=>{if(distributionAuto&&distributionPreview?.amount_per_unit!=null&&Number(quantity)>0)setExpectedDistribution((distributionPreview.amount_per_unit*Number(quantity)).toFixed(2))},[quantity,distributionAuto,distributionPreview?.amount_per_unit])

  async function handleCreatePortfolio(){
    if(newPortfolioName.trim().length<2||newPortfolioNumber.trim().length<2||creatingPortfolio||!brokerId)return
    setCreatingPortfolio(true);setMessage('')
    try{const created=await createPortfolio({name:newPortfolioName.trim(),broker_id:Number(brokerId),portfolio_number:newPortfolioNumber.replace(/\s/g,''),description:'Investment portfolio created from Trade.',currency_code:securities.find(item=>String(item.id)===securityId)?.currency_code});await refreshPortfolios();setPortfolioId(String(created.id));setNewPortfolioName('');setNewPortfolioNumber('');setMessage('Portfolio created and selected successfully.')}
    catch(error){setMessage(error instanceof Error?error.message:'Unable to create portfolio.')}
    finally{setCreatingPortfolio(false)}
  }

  function clearFields(){
    const now=new Date()
    setBrokerId('');setPortfolioId('');setSecurityId('');setSide('BUY')
    setQuantity('');setPrice('');setPriceIncludesFees(false)
    setDistributionDate('');setExpectedDistribution('');setFairValue('')
    setDistributionPreview(null);setDistributionAuto(false);setMessage('')
    setTradeDate(new Date(now.getTime()-now.getTimezoneOffset()*60000).toISOString().slice(0,16))
  }

  useEffect(() => {
    const now = new Date()

    const localDate =
      new Date(
        now.getTime() -
          now.getTimezoneOffset() *
            60000,
      )
        .toISOString()
        .slice(0, 16)

    setTradeDate(localDate)
  }, [])

  useEffect(()=>{
    const requestedPortfolio=searchParams.get('portfolio')??''
    const requestedSecurity=searchParams.get('security')??''
    if(requestedSecurity)setSecurityId(requestedSecurity)
    if(!requestedPortfolio||!portfolios.length)return
    const selected=portfolios.find(item=>String(item.id)===requestedPortfolio)
    if(!selected)return
    setPortfolioId(requestedPortfolio)
    if(selected.broker_id)setBrokerId(String(selected.broker_id))
  },[portfolios,searchParams])

  useEffect(()=>{
    if(!imported.draft)return
    const text=`${imported.draft.description} ${imported.draft.source_text}`
    setSide(/\bsell\b|بيع/i.test(text)?'SELL':'BUY')
    const importedDate=toLocalDateTime(imported.draft.transaction_date)
    if(importedDate)setTradeDate(importedDate)
    const quantityMatch=text.match(/(?:quantity|qty|كمية)\s*[:=]?\s*(\d+(?:\.\d+)?)/i)??text.match(/(\d+(?:\.\d+)?)\s*(?:shares?|units?|سهم|وحدة)/i)
    const priceMatch=text.match(/(?:price|سعر)\s*[:=@]?\s*(\d+(?:\.\d+)?)/i)??text.match(/@\s*(\d+(?:\.\d+)?)/)
    if(quantityMatch)setQuantity(quantityMatch[1])
    if(priceMatch)setPrice(priceMatch[1])
    const security=securities.find(item=>text.toLowerCase().includes(item.symbol.toLowerCase())||text.toLowerCase().includes(item.name.toLowerCase()))
    if(security)setSecurityId(String(security.id))
  },[imported.draft,securities])

  async function handleSubmit(
    event: FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault()

    if (isSubmitting) {
      return
    }

    setIsSubmitting(true)
    setMessage('')

    try {
      const posted=await createTrade({
        portfolio_id: Number(portfolioId),
        broker_id: Number(brokerId),
        security_id: Number(securityId),
        side,
        quantity: Number(quantity),
        price: effectiveUnitPrice,
        commission: Number(
          commission || 0,
        ),
        trade_date: tradeDate,
        next_distribution_date: distributionDate || undefined,
        expected_distribution_amount: expectedDistribution ? Number(expectedDistribution) : undefined,
        distribution_frequency: distributionPreview?.frequency,
        fair_value: fairValue ? Number(fairValue) : undefined,
      })

      await imported.confirm(postingReference(posted,'trade'),'SECURITY',Number(securityId))

      setMessage(
        'Trade executed successfully.',
      )

      setPortfolioId('')
      setBrokerId('')
      setSecurityId('')
      setQuantity('')
      setPrice('')
      setPriceIncludesFees(false)
      setDistributionDate('')
      setExpectedDistribution('')
      setFairValue('')

      const now = new Date()

      const localDate =
        new Date(
          now.getTime() -
            now.getTimezoneOffset() *
              60000,
        )
          .toISOString()
          .slice(0, 16)

      setTradeDate(localDate)
    } catch (error) {
      if (error instanceof Error) {
        setMessage(error.message)
      } else {
        setMessage(
          'Trade execution failed.',
        )
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <OperationForm
      title="Trade Details"
      className={side==='BUY'?'trade-operation--buy':'trade-operation--sell'}
      onSubmit={handleSubmit}
    >
      <div className="trade-operation__account-row">
        <div>
          <LookupSelect
            label="Broker"
            value={brokerId}
            options={brokers.map(
              (broker) => ({
                value: String(
                  broker.id,
                ),
                label: broker.name,
              }),
            )}
            placeholder="Select Broker"
            disabled={
              brokersLoading || isSubmitting
            }
            searchable={false}
            onChange={(value)=>{setBrokerId(value);setPortfolioId('')}}
          />
          {brokersError&&<p>{brokersError}</p>}
        </div>

        <div>
          <LookupSelect
            label="Portfolio"
            value={portfolioId}
            options={portfolios.filter(portfolio=>portfolio.broker_id===Number(brokerId)).map(portfolio=>({value:String(portfolio.id),label:portfolio.name}))}
            placeholder={brokerId?'Select Portfolio':'Select Broker First'}
            disabled={loading||isSubmitting||!brokerId}
            onChange={setPortfolioId}
          />
          {error&&<p>{error}</p>}
        </div>
      </div>
      {brokerId&&!loading&&!portfolios.some(portfolio=>portfolio.broker_id===Number(brokerId))&&<div className="trade-operation__empty-portfolio"><strong>No Portfolio For This Broker</strong><span>Create one here or manage all portfolios from the Brokers page.</span><div><input value={newPortfolioName} onChange={event=>setNewPortfolioName(event.target.value)} placeholder={`e.g. ${brokers.find(item=>item.id===Number(brokerId))?.name??''} Portfolio`}/><input value={newPortfolioNumber} onChange={event=>setNewPortfolioNumber(event.target.value)} placeholder="Portfolio Number"/><button type="button" disabled={creatingPortfolio||newPortfolioName.trim().length<2||newPortfolioNumber.trim().length<2} onClick={handleCreatePortfolio}>{creatingPortfolio?'Creating...':'Create Portfolio'}</button></div></div>}

      <div className="trade-operation__security-row">
        <div>
          <MarketSecurityLookup
            value={securityId}
            securities={securities}
            allowedCurrency={selectedPortfolio?.base_currency_code}
            disabled={
              securitiesLoading ||
              isSubmitting ||
              !portfolioId
            }
            onChange={setSecurityId}
            onRegistered={refreshSecurities}
          />
          {securitiesError && <p>{securitiesError}</p>}
        </div>
        <div className="trade-operation__side"><label>{t('Transaction Type')}</label><div><button className={`is-buy ${side==='BUY'?'is-active':''}`} type="button" onClick={()=>setSide('BUY')}>{t('Buy')}</button><button className={`is-sell ${side==='SELL'?'is-active':''}`} type="button" onClick={()=>setSide('SELL')}>{t('Sell')}</button></div></div>
      </div>
      {portfolioId?<div className={`trade-operation__cash-status ${insufficientCash?'is-insufficient':''}`}><span>{t('Portfolio Cash')}</span><strong>{formatDisplayNumber(selectedPortfolio?.cash_balance??0,{minimumFractionDigits:2,maximumFractionDigits:2},language)}</strong>{insufficientCash?<small>{t('Insufficient cash. Fund this portfolio before buying.')} <Link to={`/operations/add-cash?portfolio=${portfolioId}`}>{t('Fund Portfolio')}</Link></small>:null}</div>:null}
      <div
        className="trade-operation__value-row"
        style={{
          display: 'grid',
        }}
      >
        <div>
          <label>{t('Quantity')}</label>

          <input
            type="number"
            value={quantity}
            disabled={isSubmitting}
            onChange={(event) =>
              setQuantity(event.target.value)
            }
          />
        </div>

        <div>
          <label>{t('Price')}</label>

          <input
            type="number"
            value={price}
            disabled={isSubmitting}
            onChange={(event) =>
              setPrice(event.target.value)
            }
          />
        </div>

        <div>
          <label>{t('Total Value')}</label>

          <input
            type="text"
            value={formatDisplayNumber(totalValue,{minimumFractionDigits:2,maximumFractionDigits:2},language)}
            readOnly
            aria-label={t('Total Value Including Commission And VAT')}
          />
        </div>

        <label className="trade-operation__included-toggle"><input type="checkbox" checked={priceIncludesFees} onChange={event=>setPriceIncludesFees(event.target.checked)} disabled={isSubmitting}/><span>{t('Entered Price Includes Commission + VAT')}</span></label>
      </div>
      <div className="trade-operation__distribution">
        <div><label>{t('Next Distribution Date')}</label><input type="date" min={new Date().toISOString().slice(0,10)} value={distributionDate} disabled={isSubmitting} onChange={event=>{setDistributionDate(event.target.value);setDistributionAuto(false)}}/></div>
        <div><label>{t('Expected Distribution Amount')}</label><input type="number" min="0" step="0.01" value={expectedDistribution} disabled={isSubmitting||!distributionDate} onChange={event=>{setExpectedDistribution(event.target.value);setDistributionAuto(false)}}/></div>
        <div><label>{t('Distribution Frequency')}</label><input className="trade-operation__frequency" readOnly value={t(distributionLoading?'Checking…':distributionPreview?.frequency?distributionPreview.frequency==='SEMI_ANNUAL'?'Semi-Annual':distributionPreview.frequency==='IRREGULAR'?'Irregular / Unconfirmed':distributionPreview.frequency.charAt(0)+distributionPreview.frequency.slice(1).toLowerCase():'Not Available')}/></div>
        <p className="trade-operation__distribution-status">{distributionLoading?'Checking declared distributions…':distributionPreview?.available?distributionPreview.date_kind==='payment'?`Auto-filled from ${distributionPreview.source}.`:`${distributionPreview.source} found an eligibility date; enter the confirmed payment date manually.`:'No confirmed upcoming distribution was found. You can enter it manually.'}</p>
      </div>
      <div><label className="trade-operation__field-label"><span>{t('Expected Fair Value')}</span></label><input type="number" min="0.01" step="0.01" value={fairValue} disabled={isSubmitting} onChange={event=>setFairValue(event.target.value)} placeholder={t('Your estimated fair value per unit')}/></div>

      <div className="trade-operation__closing-row">
        <div>
          <label className="trade-operation__field-label trade-operation__commission-label"><span>{t('Commission + VAT')}</span><small>{formatDisplayNumber(baseCommission,{minimumFractionDigits:2,maximumFractionDigits:2},language)} {t('Fee')} + {formatDisplayNumber(commissionTax,{minimumFractionDigits:2,maximumFractionDigits:2},language)} {t('VAT')} ({formatDisplayPercent(selectedBroker?.commission_tax_rate??0,2,language)})</small></label>

          <input
            type="number"
            value={commission}
            readOnly
            disabled={isSubmitting||selectedBroker?.commission_rate==null}
          />
        </div>

        <div>
          <label>{t('Trade Date')}</label>

          <input
            type="datetime-local"
            value={tradeDate}
            disabled={isSubmitting}
            onChange={(event) =>
              setTradeDate(
                event.target.value,
              )
            }
          />
        </div>
      </div>
      <div className="trade-operation__actions">
        <button type="button" className="trade-operation__clear" disabled={isSubmitting} onClick={clearFields}>{t('Clear Fields')}</button>
        <button
          type="submit"
          disabled={
            isSubmitting ||
            !portfolioId ||
            !brokerId ||
            !securityId
            || insufficientCash
          }
        >
          {isSubmitting
            ? 'Executing...'
            : side==='BUY'?'Execute Buy':'Execute Sell'}
        </button>
      </div>

      {message && <p>{message}</p>}
    </OperationForm>
  )
}
