import { useEffect, useMemo, useRef, useState } from 'react'

type Option={value:string;label:string}

export default function WizardSelect({value,options,onChange,searchLabel='Search'}:{value:string;options:Option[];onChange:(value:string)=>void;searchLabel?:string}){
  const[open,setOpen]=useState(false),[query,setQuery]=useState('')
  const root=useRef<HTMLDivElement>(null),selected=useRef<HTMLButtonElement>(null)
  const visible=useMemo(()=>{const needle=query.trim().toLocaleLowerCase();return needle?options.filter(x=>x.label.toLocaleLowerCase().includes(needle)||x.value.toLocaleLowerCase().includes(needle)):options},[options,query])
  useEffect(()=>{if(!open)return;selected.current?.scrollIntoView({block:'nearest'});const close=(event:MouseEvent)=>{if(!root.current?.contains(event.target as Node))setOpen(false)};document.addEventListener('mousedown',close);return()=>document.removeEventListener('mousedown',close)},[open])
  const active=options.find(x=>x.value===value)
  return <div className={`wizard-select${open?' is-open':''}`} ref={root}>
    <button className="wizard-select__trigger" type="button" aria-haspopup="listbox" aria-expanded={open} onClick={()=>{setQuery('');setOpen(x=>!x)}}>{active?.label??value}<span>⌄</span></button>
    {open&&<div className="wizard-select__menu"><input autoFocus value={query} onChange={e=>setQuery(e.target.value)} placeholder={searchLabel}/><div role="listbox">{visible.map(option=><button type="button" role="option" aria-selected={option.value===value} ref={option.value===value?selected:undefined} className={option.value===value?'is-selected':''} key={option.value} onClick={()=>{onChange(option.value);setOpen(false)}}>{option.label}</button>)}</div></div>}
  </div>
}
