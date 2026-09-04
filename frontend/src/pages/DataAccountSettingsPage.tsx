import { AlertTriangle, DatabaseBackup, Download, ShieldAlert, Trash2 } from 'lucide-react'
import { useEffect, useState } from 'react'
import PageNavigation from '../components/ui/PageNavigation'
import { deleteAccount, getAccountBackup, getAccountProfile, type AccountProfile } from '../services/accountService'
import './SettingsSubpage.css'
import './DataAccountSettingsPage.css'
import { useLanguage } from '../context/LanguageContext'

function backupCsv(backup:Record<string,unknown>){
  const rows:Array<Record<string,unknown>>=[]
  const user=backup.user&&typeof backup.user==='object'?backup.user as Record<string,unknown>:{}
  rows.push({record_type:'account',...user})
  const data=backup.data&&typeof backup.data==='object'?backup.data as Record<string,unknown>:{}
  for(const[section,value]of Object.entries(data)){
    const records=Array.isArray(value)?value:[]
    records.forEach(record=>{if(record&&typeof record==='object')rows.push({record_type:section,...record as Record<string,unknown>})})
  }
  const columns=['record_type',...[...new Set(rows.flatMap(row=>Object.keys(row).filter(key=>key!=='record_type')))]]
  const cell=(value:unknown)=>`"${String(value??'').replaceAll('"','""')}"`
  return '\uFEFF'+[columns.map(cell).join(','),...rows.map(row=>columns.map(column=>cell(row[column])).join(','))].join('\r\n')
}

export default function DataAccountSettingsPage(){
  const{t,direction}=useLanguage()
  const[profile,setProfile]=useState<AccountProfile|null>(null);const[confirmEmail,setConfirmEmail]=useState('');const[confirmWord,setConfirmWord]=useState('');const[message,setMessage]=useState('');const[busy,setBusy]=useState(false);const[deleted,setDeleted]=useState(false)
  useEffect(()=>{getAccountProfile().then(setProfile).catch(()=>setMessage('WealthOS could not connect to your account. Please try again.'))},[])
  async function backup(){setBusy(true);setMessage('');try{const data=await getAccountBackup();const blob=new Blob(['\uFEFF',backupCsv(data)],{type:'text/csv;charset=utf-8'});const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;link.download=`wealthos-backup-${new Date().toISOString().slice(0,10)}.csv`;link.click();URL.revokeObjectURL(url);setMessage('Backup downloaded successfully.')}catch{setMessage('WealthOS could not prepare your backup. Please try again.')}finally{setBusy(false)}}
  async function remove(){if(!profile||confirmEmail.trim().toLowerCase()!==profile.email.toLowerCase()||confirmWord!=='DELETE')return;setBusy(true);setMessage('');try{await deleteAccount(confirmEmail);localStorage.clear();setDeleted(true)}catch{setMessage('Unable to delete account.');setBusy(false)}}
  if(deleted)return <section className="settings-subpage data-account" dir={direction}><section className="data-account__deleted"><ShieldAlert size={28}/><h1>{t('Account Deleted')}</h1><p>{t('Your WealthOS account and all associated financial data have been permanently deleted.')}</p></section></section>
  return <section className="settings-subpage data-account" dir={direction}><header><PageNavigation/><div className="settings-subpage__identity"><span><DatabaseBackup size={21}/></span><div><p>{t('Account Control')}</p><h1>{t('Data & Account')}</h1><small>{t('Download your information or permanently close your WealthOS account.')}</small></div></div></header>
    <section className="settings-subpage__panel data-account__backup"><div className="settings-subpage__title"><h2>{t('Account Backup')}</h2><p>{t('Download a complete copy of your financial records for safekeeping or analysis in Excel and other tools.')}</p></div><footer><span className={message.includes('successfully')?'is-success':'is-error'}>{t(message)}</span><button type="button" disabled={busy} onClick={()=>void backup()}><Download size={15}/>{t('Download Backup')}</button></footer></section>
    <section className="settings-subpage__panel data-account__danger"><div className="settings-subpage__title"><h2><AlertTriangle size={18}/>{t('Delete Account')}</h2><p>{t('This permanently deletes the account and all financial data. This action cannot be undone.')}</p></div><div className="settings-subpage__fields"><label>{t('Confirm Account Email')}<input value={confirmEmail} onChange={event=>setConfirmEmail(event.target.value)} placeholder={profile?.email??t('Loading account email…')}/></label><label>{t('Type DELETE To Confirm')}<input value={confirmWord} onChange={event=>setConfirmWord(event.target.value)} placeholder="DELETE" dir="ltr"/></label></div><footer><span>{t('Download a backup before continuing if you may need these records later.')}</span><button className="data-account__delete" type="button" disabled={busy||!profile||confirmEmail.trim().toLowerCase()!==profile.email.toLowerCase()||confirmWord!=='DELETE'} onClick={()=>void remove()}><Trash2 size={15}/>{t('Permanently Delete Account')}</button></footer></section>
  </section>
}
