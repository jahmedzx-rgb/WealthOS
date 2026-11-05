import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import OperationForm from './OperationForm'
import LookupSelect from '../components/LookupSelect'
import { useLanguage } from '../context/LanguageContext'
import { createFinancialPlatform, getFinancialPlatformCatalog, getFinancialPlatforms, type FinancialPlatform } from '../services/financialPlatformService'
import { getPlatformIconUrl } from '../utils/platformIcons'
import './AddInvestmentPlatformOperation.css'

export default function AddInvestmentPlatformOperation(){
  const{t,language}=useLanguage();const navigate=useNavigate()
  const[catalog,setCatalog]=useState<FinancialPlatform[]>([]);const[registered,setRegistered]=useState<FinancialPlatform[]>([])
  const[code,setCode]=useState('');const[message,setMessage]=useState('');const[saving,setSaving]=useState(false)
  useEffect(()=>{Promise.all([getFinancialPlatformCatalog(),getFinancialPlatforms()]).then(([directory,owned])=>{setCatalog(directory);setRegistered(owned)}).catch(()=>setMessage(t('Unable to load the platform directory.')))},[t])
  const selected=useMemo(()=>catalog.find(item=>item.code===code)??null,[catalog,code]);const alreadyAdded=registered.some(item=>item.code===code)
  const availablePlatforms=useMemo(()=>catalog.filter(item=>!registered.some(owned=>owned.code===item.code)).toSorted((left,right)=>(language==='ar'?left.name_ar:left.name).localeCompare(language==='ar'?right.name_ar:right.name,language,{sensitivity:'base'})),[catalog,registered,language])
  async function submit(event:FormEvent<HTMLFormElement>){event.preventDefault();if(!selected||alreadyAdded||saving)return;setSaving(true);setMessage('');try{await createFinancialPlatform(selected.code);navigate('/investing/platforms')}catch(reason){setMessage(t(reason instanceof Error?reason.message:'Unable to add investment platform.'));setSaving(false)}}
  const preview=<><div className="standard-operation__preview"><span>{t('Investment platform')}</span><strong>{selected?(language==='ar'?selected.name_ar:selected.name):t('Select a platform')}</strong><small>{t('The platform becomes available when recording investments.')}</small></div><div className="income-operation__effects"><h4>{t('Platform details')}</h4><p><span>{t('Country')}</span><strong>{selected?t(selected.country):'—'}</strong></p><p><span>{t('Services')}</span><strong>{selected?selected.services.map(item=>t(item.replaceAll('_',' '))).join(' · '):'—'}</strong></p><p><span>{t('Financial impact')}</span><strong>{t('None')}</strong></p></div></>
  return <OperationForm className="investment-platform-operation" title="Add Alternative Investment Platform" onSubmit={submit} preview={preview}><div className="standard-operation__grid">
    <div className="investment-platform-operation__picker"><LookupSelect label={t('Platform')} value={code} placeholder={t('Select a platform')} searchable={false} menuPlacement="bottom" options={availablePlatforms.map(item=>({value:item.code,label:language==='ar'?item.name_ar:item.name,iconUrl:getPlatformIconUrl(item.code)}))} onChange={value=>{setCode(value);setMessage('')}}/></div>
    <label><span>{t('Arabic Name')}</span><input readOnly value={selected?.name_ar??''}/></label><label><span>{t('English Name')}</span><input readOnly value={selected?.name??''}/></label>
    <label><span>{t('Country')}</span><input readOnly value={selected?.country??''}/></label><label><span>{t('Website')}</span><input readOnly value={selected?.website??''}/></label>
  </div><div className="income-operation__actions"><span>{alreadyAdded?t('This platform has already been added.'):message||t('Select from the directory; only added platforms appear in investment forms.')}</span><button type="submit" disabled={!selected||alreadyAdded||saving}>{t(saving?'Saving...':'Add Platform')}</button></div></OperationForm>
}
