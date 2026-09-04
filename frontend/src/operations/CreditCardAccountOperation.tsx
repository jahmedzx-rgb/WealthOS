import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import OperationForm from './OperationForm'
import { adjustCreditCardBalance, createCreditCardAccount, getFinancialSummary, updateCreditCard, type CreditCardAccount } from '../services/accountingService'
import { supportedCurrencies, useCurrency } from '../context/CurrencyContext'
import type { Currency } from '../context/CurrencyContext'
import { Info } from 'lucide-react'
import { formatDayMonth, formatWealthDate, normalizeWealthDateInput, parseDayMonth, parseWealthDate } from '../utils/dateFormat'
import { useLanguage } from '../context/LanguageContext'
import { formatDisplayInteger, formatDisplayPercent } from '../utils/localeFormat'

const nowLocal = () => {
  const date = new Date(Date.now() - new Date().getTimezoneOffset() * 60000)
  return date.toISOString().slice(0, 16)
}
const monthFromLocalDate=(value:string)=>String((new Date(value).getMonth()||0)+1).padStart(2,'0')
const currentMonth=()=>String(new Date().getMonth()+1).padStart(2,'0')

const nextMonthlyDate = (day:number|null) => {
  if(!day)return `/${currentMonth()}`
  const now=new Date()
  const candidate=(year:number,month:number)=>new Date(year,month,Math.min(day,new Date(year,month+1,0).getDate()))
  let result=candidate(now.getFullYear(),now.getMonth())
  if(result<new Date(now.getFullYear(),now.getMonth(),now.getDate()))result=candidate(now.getFullYear(),now.getMonth()+1)
  return formatDayMonth(result)
}

function FieldInfo({label,text}:{label:string;text:string}) {
  const [open,setOpen]=useState(false)
  const{t}=useLanguage()
  return <span className={`operation-field__info${open?' is-open':''}`} role="button" tabIndex={0} aria-label={t(label)} aria-expanded={open} data-tooltip={t(text)} onMouseDown={(event)=>event.preventDefault()} onClick={(event)=>{event.preventDefault();event.stopPropagation();setOpen(current=>!current)}} onKeyDown={(event)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();event.stopPropagation();setOpen(current=>!current)}}} onMouseLeave={()=>setOpen(false)} onBlur={()=>setOpen(false)}><Info size={13}/></span>
}

function DayMonthInput({value,onChange,disabled=false}:{value:string;onChange:(value:string)=>void;disabled?:boolean}) {
  const{t,language}=useLanguage()
  const [day='',month=currentMonth()]=value.split('/')
  const months=Array.from({length:12},(_,index)=>String(index+1).padStart(2,'0'))
  return <span className={`credit-card-operation__day-month${disabled?' is-disabled':''}`}><input aria-label={t('Day')} inputMode="numeric" maxLength={2} placeholder={t('DD')} value={day} disabled={disabled} onChange={(event)=>onChange(`${event.target.value.replace(/\D/g,'').slice(0,2)}/${month}`)} onBlur={()=>{if(day.length===1)onChange(`${day.padStart(2,'0')}/${month}`)}}/><i>/</i><select aria-label={t('Month')} value={month} disabled={disabled} onChange={(event)=>onChange(`${day}/${event.target.value}`)}>{months.map(item=><option value={item} key={item}>{formatDisplayInteger(Number(item),language)}</option>)}</select></span>
}

export default function CreditCardAccountOperation() {
  const { baseCurrency, enabledCurrencies, formatMoney } = useCurrency()
  const { language } = useLanguage()
  const [searchParams] = useSearchParams()
  const editCardId = searchParams.get('edit')
  const editMode = Boolean(editCardId)
  const [form, setForm] = useState({ issuer_bank:'', card_name:'', last4:'', credit_limit:'', used_balance:'', statement_balance:'', minimum_monthly_payment:'', statement_cutoff_day:`/${currentMonth()}`, payment_due_day:`/${currentMonth()}`, is_fee_free:false, annual_fee:'', fee_renewal_date:`/${currentMonth()}`, currency_code:baseCurrency, as_of_date:nowLocal() })
  const [cards, setCards] = useState<CreditCardAccount[]>([])
  const [status, setStatus] = useState('')
  const [saving, setSaving] = useState(false)
  const [adjusting,setAdjusting]=useState(false)
  const [adjustment,setAdjustment]=useState({corrected_balance:'',adjustment_date:formatWealthDate(new Date()),reason:''})
  const limit = Number(form.credit_limit) || 0
  const used = Number(form.used_balance) || 0
  const statementBalance = Number(form.statement_balance) || 0
  const available = Math.max(0, limit-used)
  const utilization = limit ? used/limit*100 : 0
  const monthlyObligation = Number(form.minimum_monthly_payment) || used * .05
  const update = (key:string, value:string) => setForm((current)=>({...current,[key]:value}))
  const updateBalanceDate=(value:string)=>setForm((current)=>{const oldMonth=monthFromLocalDate(current.as_of_date),newMonth=monthFromLocalDate(value);const sync=(date:string)=>{const [day,month]=date.split('/');return month===oldMonth?`${day}/${newMonth}`:date};return {...current,as_of_date:value,statement_cutoff_day:sync(current.statement_cutoff_day),payment_due_day:sync(current.payment_due_day),fee_renewal_date:sync(current.fee_renewal_date)}})
  useEffect(() => {
    if (!editMode) return
    getFinancialSummary().then((summary) => {
      setCards(summary.credit_cards)
      const card = summary.credit_cards.find((item)=>String(item.id)===editCardId)
      if (card) {
        setForm((current)=>({...current,issuer_bank:card.issuer_bank,card_name:card.card_name,last4:card.last4,credit_limit:String(card.credit_limit),used_balance:String(card.current_balance),statement_balance:String(card.statement_balance),minimum_monthly_payment:String(card.minimum_monthly_payment||''),statement_cutoff_day:nextMonthlyDate(card.statement_cutoff_day),payment_due_day:nextMonthlyDate(card.payment_due_day),is_fee_free:card.is_fee_free,annual_fee:String(card.annual_fee||''),fee_renewal_date:card.fee_renewal_day&&card.fee_renewal_month?`${String(card.fee_renewal_day).padStart(2,'0')}/${String(card.fee_renewal_month).padStart(2,'0')}`:`/${currentMonth()}`,currency_code:card.currency_code as Currency}))
      } else {
        setStatus('Credit card not found.')
      }
    }).catch(()=>setStatus('Unable to load your credit cards.'))
  }, [editMode,editCardId])
  const submit = async (event:FormEvent) => {
    event.preventDefault()
    setStatus('')
    const cutoffDate=parseDayMonth(form.statement_cutoff_day), dueDate=parseDayMonth(form.payment_due_day), renewalDate=parseDayMonth(form.fee_renewal_date)
    const cutoff=cutoffDate?.day??0, due=dueDate?.day??0
    if (!cutoffDate||!dueDate) {
      setStatus('Enter valid statement cutoff and payment due dates in DD/MM format.')
      return
    }
    if(!form.is_fee_free&&((Number(form.annual_fee)||0)<=0||!renewalDate)){setStatus('Enter the annual fee and its renewal date, or mark the card as free.');return}
    if (editMode) {
      if (!editCardId || !form.issuer_bank.trim() || !form.card_name.trim() || !/^\d{4}$/.test(form.last4) || limit<=0 || limit<used || statementBalance>used) {
        setStatus(statementBalance>used?'Statement balance cannot exceed current credit used.':limit<used?'Credit limit cannot be lower than the current used balance.':'Complete the required card details.')
        return
      }
      setSaving(true)
      try { await updateCreditCard(Number(editCardId),{issuer_bank:form.issuer_bank,card_name:form.card_name,last4:form.last4,credit_limit:limit,statement_balance:statementBalance,minimum_monthly_payment:Number(form.minimum_monthly_payment)||0,statement_cutoff_day:cutoff,payment_due_day:due,is_fee_free:form.is_fee_free,annual_fee:form.is_fee_free?0:Number(form.annual_fee)||0,fee_renewal_day:form.is_fee_free?null:renewalDate?.day??null,fee_renewal_month:form.is_fee_free?null:renewalDate?.month??null,currency_code:form.currency_code}); setStatus('Credit card details updated successfully.') }
      catch(error){setStatus(error instanceof Error?error.message:'Unable to update the credit card.')}
      finally{setSaving(false)}
      return
    }
    if (!form.issuer_bank.trim() || !form.card_name.trim() || !/^\d{4}$/.test(form.last4) || limit<=0 || used>limit || statementBalance>used) {
      setStatus(statementBalance>used?'Statement balance cannot exceed current credit used.':used>limit?'Credit used cannot exceed the credit limit.':'Complete the required card details.')
      return
    }
    setSaving(true)
    try {
      await createCreditCardAccount({...form, credit_limit:limit, used_balance:used, statement_balance:statementBalance, minimum_monthly_payment:Number(form.minimum_monthly_payment)||0, statement_cutoff_day:cutoff, payment_due_day:due, annual_fee:form.is_fee_free?0:Number(form.annual_fee)||0,fee_renewal_day:form.is_fee_free?null:renewalDate?.day??null,fee_renewal_month:form.is_fee_free?null:renewalDate?.month??null, as_of_date:new Date(form.as_of_date).toISOString()})
      setStatus('Credit card saved and its opening balance was posted to liabilities.')
      setForm({ issuer_bank:'', card_name:'', last4:'', credit_limit:'', used_balance:'', statement_balance:'', minimum_monthly_payment:'', statement_cutoff_day:`/${currentMonth()}`, payment_due_day:`/${currentMonth()}`, is_fee_free:false, annual_fee:'', fee_renewal_date:`/${currentMonth()}`, currency_code:baseCurrency, as_of_date:nowLocal() })
    } catch (error) { setStatus(error instanceof Error?error.message:'Unable to save the credit card.') }
    finally { setSaving(false) }
  }
  const saveAdjustment = async () => {
    if(!editCardId)return
    const corrected=Number(adjustment.corrected_balance), date=parseWealthDate(adjustment.adjustment_date)
    if(!Number.isFinite(corrected)||corrected<0||corrected>limit){setStatus('Enter a corrected balance between zero and the credit limit.');return}
    if(!date||adjustment.reason.trim().length<3){setStatus('Enter a valid adjustment date and a brief reason.');return}
    setSaving(true);setStatus('')
    try{const card=await adjustCreditCardBalance(Number(editCardId),{corrected_balance:corrected,adjustment_date:date.toISOString(),reason:adjustment.reason.trim()});setForm(current=>({...current,used_balance:String(card.current_balance)}));setStatus('Card balance adjusted and the accounting correction was posted.');setAdjusting(false);setAdjustment({corrected_balance:'',adjustment_date:formatWealthDate(new Date()),reason:''})}
    catch(error){setStatus(error instanceof Error?error.message:'Unable to adjust the card balance.')}
    finally{setSaving(false)}
  }
  if(editMode)return <OperationForm title="Edit Credit Card" onSubmit={(event)=>void submit(event)} preview={<>
    <div className="standard-operation__preview"><span>Current used balance</span><strong>{formatMoney(used,form.currency_code as Currency)}</strong><small>Updated only through posted card transactions</small></div>
    <div className="income-operation__effects"><h4>Card position</h4><p><span>Credit limit</span><strong>{formatMoney(limit,form.currency_code as Currency)}</strong></p><p><span>Available credit</span><strong>{formatMoney(available,form.currency_code as Currency)}</strong></p><p><span>Utilization</span><strong>{formatDisplayPercent(utilization,1,language)}</strong></p></div>
  </>}>
    <div className="standard-operation__grid credit-card-operation__grid">
      <div className="credit-card-operation__identity-row">
        <label><span>Issuer Bank</span><input value={form.issuer_bank} onChange={(e)=>update('issuer_bank',e.target.value)} /></label>
        <label><span>Card Name</span><input value={form.card_name} onChange={(e)=>update('card_name',e.target.value)} /></label>
        <label><span>Last 4 Digits</span><input value={form.last4} maxLength={4} inputMode="numeric" onChange={(e)=>update('last4',e.target.value.replace(/\D/g,''))} /></label>
      </div>
      <div className="credit-card-operation__balance-row">
        <label><span>Credit Limit</span><input type="number" min={used} step="0.01" value={form.credit_limit} onChange={(e)=>update('credit_limit',e.target.value)} /></label>
        <label><span>Credit Used</span><input type="number" value={form.used_balance} readOnly /></label>
        <label><span>Statement Balance <FieldInfo label="About statement balance" text="The amount due from the latest issued statement. Newer card purchases remain in Credit Used but are not included here." /></span><input type="number" min="0" max={used} step="0.01" value={form.statement_balance} onChange={(e)=>update('statement_balance',e.target.value)} /></label>
        <label><span><span className="credit-card-operation__minimum-label">Minimum Monthly<br/>Payment</span><em className="operation-field__optional">Optional</em><FieldInfo label="About minimum monthly payment" text="The minimum amount shown on your card statement. It is included in DBR. If left empty, WealthOS estimates it as 5% of the current card balance." /></span><input type="number" min="0" step="0.01" value={form.minimum_monthly_payment} onChange={(e)=>update('minimum_monthly_payment',e.target.value)} /></label>
      </div>
      <div className="credit-card-operation__schedule-row">
        <label><span>Cutoff Date <FieldInfo label="About cutoff date" text="Enter the day. The month follows the transaction date automatically and remains editable." /></span><DayMonthInput value={form.statement_cutoff_day} onChange={(value)=>update('statement_cutoff_day',value)} /></label>
        <label><span>Due Date <FieldInfo label="About due date" text="Enter the day. The month follows the transaction date automatically and remains editable." /></span><DayMonthInput value={form.payment_due_day} onChange={(value)=>update('payment_due_day',value)} /></label>
        <label><span>Currency <FieldInfo label="About card currency" text="A card with an outstanding balance keeps its original currency. Settle the card in full before changing its currency." /></span><select value={form.currency_code} onChange={(e)=>update('currency_code',e.target.value as Currency)} disabled={used>0}>{enabledCurrencies.map(code=>{const item=supportedCurrencies.find(currency=>currency.code===code);return <option key={code} value={code}>{item?.symbol} - {item?.name}</option>})}</select></label>
      </div>
      <aside className="credit-card-operation__fee-row">
        <header><strong>Card Costs</strong><small>Annual card charges</small></header>
        <label className="credit-card-operation__free-card"><span>Fee Type</span><button type="button" role="checkbox" aria-checked={form.is_fee_free} className={form.is_fee_free?'is-selected':''} onClick={()=>setForm(current=>({...current,is_fee_free:!current.is_fee_free}))}><i>{form.is_fee_free?'✓':''}</i> Free Card</button></label>
        <label><span>Annual Fee</span><input type="number" min="0" step="0.01" value={form.annual_fee} disabled={form.is_fee_free} onChange={(e)=>update('annual_fee',e.target.value)} /></label>
        <label><span>Fee Renewal Date</span><DayMonthInput value={form.fee_renewal_date} disabled={form.is_fee_free} onChange={(value)=>update('fee_renewal_date',value)} /></label>
      </aside>
      <div className="credit-card-operation__balance-tools"><button className="credit-card-operation__adjust" type="button" onClick={()=>{setAdjusting(current=>!current);setAdjustment(current=>({...current,corrected_balance:form.used_balance}))}}>Adjust Balance</button><FieldInfo label="About balance adjustments" text="Use this only to correct a mismatch with the bank statement. Frequent adjustments create accounting corrections and can reduce the reliability of your financial history." /></div>
    </div>
    {adjusting?<section className="credit-card-operation__adjustment"><header><strong>Balance Adjustment</strong><small>Posts an accounting correction to this card.</small></header><div><label><span>Corrected Balance</span><input type="number" min="0" max={limit} step="0.01" value={adjustment.corrected_balance} onChange={(e)=>setAdjustment(current=>({...current,corrected_balance:e.target.value}))}/></label><label><span>Adjustment Date</span><input inputMode="numeric" maxLength={10} placeholder="DD/MM/YYYY" value={adjustment.adjustment_date} onChange={(e)=>setAdjustment(current=>({...current,adjustment_date:normalizeWealthDateInput(e.target.value)}))}/></label><label><span>Reason</span><input value={adjustment.reason} maxLength={240} placeholder="Why is this correction needed?" onChange={(e)=>setAdjustment(current=>({...current,reason:e.target.value}))}/></label></div><footer><button type="button" onClick={()=>setAdjusting(false)}>Cancel</button><button type="button" disabled={saving} onClick={()=>void saveAdjustment()}>{saving?'Posting…':'Post Adjustment'}</button></footer></section>:null}
    <div className="income-operation__actions"><span>{status||'Balance changes remain protected and follow posted transactions.'}</span><button type="submit" disabled={saving||!cards.length}>{saving?'Saving…':'Save Changes'}</button></div>
  </OperationForm>
  return <OperationForm title="Credit card details" onSubmit={(event)=>void submit(event)} preview={<>
    <div className="standard-operation__preview"><span>Total credit limit</span><strong>{formatMoney(limit)}</strong><small>{formatDisplayPercent(utilization,1,language)} utilized</small></div>
    <div className="income-operation__effects"><h4>Financial impact</h4><p><span>Credit used</span><strong>{formatMoney(used)}</strong></p><p><span>Available credit</span><strong>{formatMoney(available)}</strong></p><p><span>Monthly DBR obligation</span><strong>{formatMoney(monthlyObligation)}</strong></p></div>
  </>}>
    <div className="standard-operation__grid credit-card-operation__grid">
      <div className="credit-card-operation__identity-row">
        <label><span>Issuer Bank</span><input value={form.issuer_bank} onChange={(e)=>update('issuer_bank',e.target.value)} placeholder="Bank name" /></label>
        <label><span>Card Name</span><input value={form.card_name} onChange={(e)=>update('card_name',e.target.value)} placeholder="e.g. Visa Infinite" /></label>
        <label><span>Last 4 Digits</span><input value={form.last4} maxLength={4} inputMode="numeric" onChange={(e)=>update('last4',e.target.value.replace(/\D/g,''))} placeholder="0000" /></label>
      </div>
      <div className="credit-card-operation__balance-row">
        <label><span>Credit Limit</span><input type="number" min="0" step="0.01" value={form.credit_limit} onChange={(e)=>update('credit_limit',e.target.value)} /></label>
        <label><span>Credit Used</span><input type="number" min="0" step="0.01" value={form.used_balance} onChange={(e)=>update('used_balance',e.target.value)} /></label>
        <label><span>Statement Balance <FieldInfo label="About statement balance" text="Enter the amount due on the latest issued statement. Leave newer purchases only in Credit Used." /></span><input type="number" min="0" max={used} step="0.01" value={form.statement_balance} onChange={(e)=>update('statement_balance',e.target.value)} /></label>
        <label><span><span className="credit-card-operation__minimum-label">Minimum Monthly<br/>Payment</span><em className="operation-field__optional">Optional</em><FieldInfo label="About minimum monthly payment" text="The minimum amount shown on your card statement. It is included in DBR. If left empty, WealthOS estimates it as 5% of the current card balance." /></span><input type="number" min="0" step="0.01" value={form.minimum_monthly_payment} onChange={(e)=>update('minimum_monthly_payment',e.target.value)} /></label>
      </div>
      <div className="credit-card-operation__schedule-row">
        <label><span>Cutoff Date <FieldInfo label="About cutoff date" text="Enter the day. The month follows the transaction date automatically and remains editable." /></span><DayMonthInput value={form.statement_cutoff_day} onChange={(value)=>update('statement_cutoff_day',value)} /></label>
        <label><span>Due Date <FieldInfo label="About due date" text="Enter the day. The month follows the transaction date automatically and remains editable." /></span><DayMonthInput value={form.payment_due_day} onChange={(value)=>update('payment_due_day',value)} /></label>
        <label><span>Currency <FieldInfo label="About card currency" text="The card currency is selected from your enabled currencies. Your base currency is selected automatically for a new card." /></span><select value={form.currency_code} onChange={(e)=>update('currency_code',e.target.value as Currency)}>{enabledCurrencies.map(code=>{const item=supportedCurrencies.find(currency=>currency.code===code);return <option key={code} value={code}>{item?.symbol} - {item?.name}</option>})}</select></label>
      </div>
      <aside className="credit-card-operation__fee-row">
        <header><strong>Card Costs</strong><small>Annual card charges</small></header>
        <label className="credit-card-operation__free-card"><span>Fee Type</span><button type="button" role="checkbox" aria-checked={form.is_fee_free} className={form.is_fee_free?'is-selected':''} onClick={()=>setForm(current=>({...current,is_fee_free:!current.is_fee_free}))}><i>{form.is_fee_free?'✓':''}</i> Free Card</button></label>
        <label><span>Annual Fee</span><input type="number" min="0" step="0.01" value={form.annual_fee} disabled={form.is_fee_free} onChange={(e)=>update('annual_fee',e.target.value)} /></label>
        <label><span>Fee Renewal Date</span><DayMonthInput value={form.fee_renewal_date} disabled={form.is_fee_free} onChange={(value)=>update('fee_renewal_date',value)} /></label>
      </aside>
      <label className="credit-card-operation__balance-date"><span>Balance Date</span><input type="datetime-local" value={form.as_of_date} onChange={(e)=>updateBalanceDate(e.target.value)} /></label>
    </div>
    <div className="income-operation__actions"><span>{status || 'The full used balance becomes a liability; DBR uses the entered payment or estimates 5% when left empty.'}</span><button type="submit" disabled={saving}>{saving?'Saving…':'Add Credit Card'}</button></div>
  </OperationForm>
}
