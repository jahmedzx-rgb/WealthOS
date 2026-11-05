import { useEffect, useRef, type ChangeEvent, type InputHTMLAttributes } from 'react'
import { useLanguage } from '../context/LanguageContext'
import { displayAmountInput, parseAmountInput } from '../utils/amountInput'

type Props=Omit<InputHTMLAttributes<HTMLInputElement>,'value'|'type'> & {value:string|number;type?:'number';decimalPlaces?:number;allowNegative?:boolean}

export default function AmountInput({value,onChange,min,max,step: _step,type: _type,decimalPlaces=2,allowNegative=false,...props}:Props) {
  const {language}=useLanguage()
  const ref=useRef<HTMLInputElement>(null)
  const raw=String(value)
  useEffect(()=>{
    const validPrecision=new RegExp(`^${allowNegative?'-?':''}\\d+(\\.\\d{0,${decimalPlaces}})?$`)
    const invalid=raw!==''&&(!validPrecision.test(raw)||!Number.isFinite(Number(raw))||(min!==undefined&&Number(raw)<Number(min))||(max!==undefined&&Number(raw)>Number(max)))
    ref.current?.setCustomValidity(invalid?(language==='ar'?`أدخل رقمًا صحيحًا ضمن النطاق المسموح وبحد أقصى ${decimalPlaces} منازل عشرية.`:`Enter a valid number within the allowed range, with at most ${decimalPlaces} decimal places.`):'')
  },[raw,min,max,language,decimalPlaces,allowNegative])
  return <input {...props} ref={ref} type="text" inputMode="decimal" dir="ltr" value={displayAmountInput(raw,language)} onChange={event=>{
    const next=parseAmountInput(event.target.value)
    if(!(allowNegative?/^-?\d*(\.\d*)?$/:/^\d*(\.\d*)?$/).test(next))return
    onChange?.({...event,target:{...event.target,value:next},currentTarget:{...event.currentTarget,value:next}} as ChangeEvent<HTMLInputElement>)
  }}/>
}
