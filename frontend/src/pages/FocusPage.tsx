import { CalendarClock, CheckCircle2, ListTodo } from 'lucide-react'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import PageNavigation from '../components/ui/PageNavigation'
import { useLiveFocusItems } from '../hooks/useLiveFocusItems'
import './FocusPage.css'

export default function FocusPage(){
  const navigate=useNavigate()
  const {items,loading}=useLiveFocusItems()
  const [filter,setFilter]=useState('All')
  const visible=useMemo(()=>items.filter(item=>filter==='All'||item.priority===filter.toLowerCase()),[items,filter])
  return <section className="focus-page">
    <header><PageNavigation/><div className="focus-page__identity"><span><ListTodo size={21}/></span><div><p>Personal attention center</p><h1>Focus</h1><small>Real upcoming obligations and distribution events.</small></div></div></header>
    <div className="focus-page__metrics"><article><span>Needs attention</span><strong>{items.length}</strong><small>Live items</small></article><article><span>Upcoming distributions</span><strong>{items.filter(item=>item.id.startsWith('distribution-')).length}</strong><small>Next 30 days</small></article><article><span>High priority</span><strong>{items.filter(item=>item.priority==='high').length}</strong><small>Act soon</small></article></div>
    <section className="focus-page__panel"><div className="focus-page__toolbar"><div><h2>All focus items</h2><p>Ordered from your posted data</p></div><nav>{['All','High','Medium','Low'].map(value=><button className={filter===value?'is-active':''} type="button" onClick={()=>setFilter(value)} key={value}>{value}</button>)}</nav></div><div className="focus-page__list">{visible.map(item=><article key={item.id}><i className={`is-${item.priority}`}>{item.icon}</i><div><strong>{item.title}</strong><small><CalendarClock size={13}/>{item.subtitle}</small></div><em className={`is-${item.priority}`}>{item.priority}</em><b>{item.amount??'Review'}</b><button type="button" onClick={()=>navigate(item.route)}><CheckCircle2 size={16}/>Open</button></article>)}{!loading&&!visible.length&&<div className="focus-page__empty"><CheckCircle2 size={22}/><strong>You’re all caught up</strong><span>No live items match this filter.</span></div>}</div></section>
  </section>
}
