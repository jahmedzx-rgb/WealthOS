import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { Pencil, Plus, WalletCards, X } from 'lucide-react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import DateInput from '../components/DateInput'
import FormattedMoney from '../components/ui/FormattedMoney'
import { useCurrency } from '../context/CurrencyContext'
import { useLanguage } from '../context/LanguageContext'
import { createDigitalWallet, getDigitalWallets, updateDigitalWallet, type BankAccount } from '../services/accountingService'
import './DigitalWalletsPage.css'
import './DigitalWalletsPanelHeader.css'
import './DigitalWalletLogos.css'

const providers=['Barq','urpay','Mobily Pay','Hala','Tiqmo','Alinma Pay','Other']
const localNow=()=>new Date(Date.now()-new Date().getTimezoneOffset()*60000).toISOString().slice(0,16)
const cleanLast4=(value:string)=>value.replace(/\D/g,'').slice(-4)
const providerClass=(provider:string)=>`is-${provider.toLowerCase().replace(/[^a-z0-9]+/g,'-')}`
const providerLogo=(provider:string)=>{
  const normalized=provider.trim().toLowerCase()
  if(normalized==='barq')return '/wallets/barq-icon.svg'
  if(normalized==='alinma pay')return '/wallets/alinma-pay-icon.png'
  return null
}

export default function DigitalWalletsPage({createMode=false}:{createMode?:boolean}){
  const {formatMoney,currency}=useCurrency();const {t}=useLanguage()
  const [wallets,setWallets]=useState<BankAccount[]>([]);const[editing,setEditing]=useState<BankAccount|null|undefined>(undefined);const[message,setMessage]=useState('');const[saving,setSaving]=useState(false)
  const [form,setForm]=useState({provider:'Barq',customProvider:'',name:'',identifier:'',currency,openingBalance:'',date:localNow()})
  const load=()=>getDigitalWallets().then(setWallets).catch(error=>setMessage(error instanceof Error?error.message:t('Unable to load digital wallets.')))
  useEffect(()=>{void load()},[])
  const total=useMemo(()=>wallets.reduce((sum,item)=>sum+Number(item.current_balance),0),[wallets])
  const open=(wallet?:BankAccount)=>{setMessage('');setEditing(wallet??null);setForm(wallet?{provider:providers.includes(wallet.bank_name)?wallet.bank_name:'Other',customProvider:providers.includes(wallet.bank_name)?'':wallet.bank_name,name:wallet.account_name,identifier:wallet.account_identifier,currency:wallet.currency_code as typeof currency,openingBalance:'',date:localNow()}:{provider:'Barq',customProvider:'',name:'',identifier:'',currency,openingBalance:'',date:localNow()})}
  useEffect(()=>{if(createMode)open()},[createMode])
  async function submit(event:FormEvent){event.preventDefault();const provider=form.provider==='Other'?form.customProvider.trim():form.provider;if(!provider||cleanLast4(form.identifier).length<4)return;setSaving(true);setMessage('');try{if(editing)await updateDigitalWallet(editing.id,{bank_name:provider,account_type:'DIGITAL_WALLET',account_name:form.name.trim()||provider,account_identifier:form.identifier,correction_reason:'Wallet details updated'});else await createDigitalWallet({bank_name:provider,account_type:'DIGITAL_WALLET',account_name:form.name.trim()||provider,account_identifier:form.identifier,currency_code:form.currency,opening_balance:Number(form.openingBalance||0),as_of_date:new Date(form.date).toISOString(),is_primary:false});setEditing(undefined);setMessage(t(editing?'Digital wallet updated successfully.':'Digital wallet added successfully.'));await load()}catch(error){setMessage(error instanceof Error?error.message:t('Unable to save the digital wallet.'))}finally{setSaving(false)}}
  return <section className="wallets-page"><PageHeader title={t('E-Wallets')} subtitle={t('Track wallet balances separately from bank accounts.')} icon={WalletCards} actions={<Link className="page-header__primary-action" to="/e-wallets/new"><Plus size={16}/>{t('Add E-Wallet')}</Link>}/>
    <div className="wallets-page__metrics"><article><span>{t('Wallet Balance')}</span><strong><FormattedMoney value={formatMoney(total)}/></strong><small>{t('Across all digital wallets')}</small></article><article><span>{t('Active Wallets')}</span><strong>{wallets.length}</strong><small>{t('Registered providers')}</small></article></div>
    {message&&<p className="wallets-page__message">{message}</p>}
    <section className="wallets-page__panel"><header><div><h2>{t('Wallet Accounts')}</h2><p>{t('Electronic money accounts and wallet providers')}</p></div></header><div className="wallets-page__list">{wallets.map(wallet=>{const logo=providerLogo(wallet.bank_name);return <article key={wallet.id}><span className={`wallets-page__provider ${providerClass(wallet.bank_name)}`}>{logo?<img src={logo} alt={wallet.bank_name}/>:wallet.bank_name.slice(0,1).toUpperCase()}</span><div><strong>{wallet.account_name||wallet.bank_name}</strong><small>{wallet.bank_name} · ••••{cleanLast4(wallet.account_identifier)}</small></div><b><FormattedMoney value={formatMoney(Number(wallet.current_balance),wallet.currency_code as typeof currency)}/></b><em>{wallet.currency_code}</em><button type="button" onClick={()=>open(wallet)}><Pencil size={14}/>{t('Edit')}</button></article>})}{!wallets.length&&<div className="wallets-page__empty"><WalletCards size={25}/><strong>{t('No digital wallets yet')}</strong><span>{t('Add your first wallet to begin tracking its balance.')}</span></div>}</div></section>
    {editing!==undefined&&<div className="wallet-dialog" onMouseDown={event=>{if(event.target===event.currentTarget)setEditing(undefined)}}><form onSubmit={submit}><header><div><small>{t(editing?'Edit Wallet':'New Wallet')}</small><h2>{t('Digital Wallet Details')}</h2></div><button type="button" onClick={()=>setEditing(undefined)}><X size={18}/></button></header><div className="wallet-dialog__grid"><label><span>{t('Wallet Provider')}</span><select value={form.provider} onChange={e=>setForm({...form,provider:e.target.value})}>{providers.map(provider=><option key={provider}>{provider}</option>)}</select></label>{form.provider==='Other'&&<label><span>{t('Provider Name')}</span><input required value={form.customProvider} onChange={e=>setForm({...form,customProvider:e.target.value})}/></label>}<label><span>{t('Wallet Name')}</span><input value={form.name} onChange={e=>setForm({...form,name:e.target.value})} placeholder={t('e.g. Main Wallet')}/></label><label><span>{t('Wallet Number')}</span><input required minLength={4} value={form.identifier} onChange={e=>setForm({...form,identifier:e.target.value})} placeholder={t('Mobile number or wallet ID')}/></label><label><span>{t('Currency')}</span><input readOnly value={form.currency}/></label>{!editing&&<><label><span>{t('Opening Balance')}</span><input type="number" min="0" step=".01" value={form.openingBalance} onChange={e=>setForm({...form,openingBalance:e.target.value})} placeholder="0.00"/></label><label><span>{t('Balance Date')}</span><DateInput type="datetime-local" required value={form.date} onChange={e=>setForm({...form,date:e.target.value})}/></label></>}</div><footer><button type="button" onClick={()=>setEditing(undefined)}>{t('Cancel')}</button><button type="submit" disabled={saving}>{t(saving?'Saving…':editing?'Save Changes':'Add Wallet')}</button></footer></form></div>}
  </section>
}
