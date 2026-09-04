import { Check, CircleDashed, FileCheck2, Scale, ShieldCheck } from 'lucide-react'
import { useLanguage } from '../../context/LanguageContext'

type Props={requiredComplete:boolean;balanced:boolean;recorded:boolean}

export default function OperationPreflight({requiredComplete,balanced,recorded}:Props){
  const {t}=useLanguage()
  const ready=requiredComplete&&balanced
  const items=[
    {label:'Required Fields',value:requiredComplete?'Complete':'Missing Details',complete:requiredComplete,icon:ShieldCheck},
    {label:'Journal Entry',value:balanced?'Balanced':'Waiting for Values',complete:balanced,icon:Scale},
    {label:'Audit Trail',value:recorded?'Recorded':ready?'Will Be Recorded':'Pending',complete:recorded||ready,icon:FileCheck2},
  ]
  return <section className={`operation-preflight${ready?' is-ready':''}${recorded?' is-recorded':''}`} aria-label={t('Operation readiness')}>
    <header><div><small>{t('Preflight Check')}</small><strong>{t(recorded?'Operation Recorded':ready?'Ready for Review':'Complete Required Details')}</strong></div><span>{recorded?<Check size={15}/>:ready?<Check size={15}/>:<CircleDashed size={15}/>}</span></header>
    <div>{items.map(item=>{const Icon=item.icon;return <p className={item.complete?'is-complete':''} key={item.label}><span><i><Icon size={13}/></i>{t(item.label)}</span><strong>{t(item.value)}</strong></p>})}</div>
  </section>
}
