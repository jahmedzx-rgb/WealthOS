import { CheckCircle2, Copy, Link2, QrCode, RefreshCw, ShieldCheck, Smartphone, Trash2 } from 'lucide-react'
import QRCode from 'qrcode'
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import PageNavigation from '../components/ui/PageNavigation'
import { useLanguage } from '../context/LanguageContext'
import { createMobilePairing, getMobileDevices, revokeMobileDevice, updateMobileDeviceSenders, type MobileDevice, type MobilePairing } from '../services/mobileBridgeService'
import { formatDateTime } from '../utils/dateFormat'
import './SettingsSubpage.css'
import './MobileConnectionsPage.css'

const DEFAULT_SENDERS=['SNB','ANB','NBD','D360','ALINMA','ALRAJHI','SAB','SAIB','BSF']

export default function MobileConnectionsPage(){
  const{direction}=useLanguage()
  const[devices,setDevices]=useState<MobileDevice[]>([]),[pairing,setPairing]=useState<MobilePairing|null>(null),[qr,setQr]=useState(''),[senders,setSenders]=useState(DEFAULT_SENDERS.join(', ')),[message,setMessage]=useState(''),[busy,setBusy]=useState(false)
  const senderList=useMemo(()=>Array.from(new Set(senders.split(/[\n,]+/).map(value=>value.trim()).filter(Boolean))),[senders])
  const active=devices.filter(device=>device.status==='ACTIVE')
  const lastSync=active.map(device=>device.last_sync_at).filter((value):value is string=>Boolean(value)).sort().at(-1)
  async function load(){try{setDevices(await getMobileDevices())}catch(error){setMessage(error instanceof Error?error.message:'Unable to load connected devices.')}}
  useEffect(()=>{void load()},[])
  useEffect(()=>{if(!pairing){setQr('');return}const payload=JSON.stringify({version:1,api_base:`${window.location.origin}/api/v1`,pairing_secret:pairing.pairing_secret});QRCode.toDataURL(payload,{width:280,margin:1,errorCorrectionLevel:'M',color:{dark:'#102744',light:'#ffffff'}}).then(setQr).catch(()=>setQr(''))},[pairing])
  async function pair(){setBusy(true);setMessage('');try{setPairing(await createMobilePairing(senderList))}catch(error){setMessage(error instanceof Error?error.message:'Unable to create pairing code.')}finally{setBusy(false)}}
  async function saveSenders(device:MobileDevice){setBusy(true);setMessage('');try{await updateMobileDeviceSenders(device.id,senderList);await load();setMessage('Sender list updated.')}catch(error){setMessage(error instanceof Error?error.message:'Unable to update sender list.')}finally{setBusy(false)}}
  async function revoke(device:MobileDevice){if(!window.confirm(`Revoke ${device.device_name}? The phone can be paired again later.`))return;setBusy(true);try{await revokeMobileDevice(device.id);await load();setMessage('Device access revoked.')}catch(error){setMessage(error instanceof Error?error.message:'Unable to revoke device.')}finally{setBusy(false)}}
  async function copySecret(){if(!pairing)return;await navigator.clipboard.writeText(pairing.pairing_secret);setMessage('Pairing code copied. It expires in 10 minutes.')}
  return <section className="settings-subpage mobile-connections" dir={direction}><header><PageNavigation/><div className="settings-subpage__identity"><span><Smartphone size={21}/></span><div><p>MOBILE INTEGRATION</p><h1>WealthOS Connect</h1><small>Securely import financial SMS messages from your Android phone.</small></div></div></header>
    <div className="mobile-connections__metrics"><article><span>Active devices</span><strong>{active.length}</strong><small>Revocable device access</small></article><article><span>Last phone sync</span><strong>{lastSync?formatDateTime(lastSync):'Not synced'}</strong><small>Messages remain review-only</small></article><article><span>Posting policy</span><strong>Review required</strong><small>No automatic ledger posting</small></article></div>
    <section className="settings-subpage__panel"><div className="settings-subpage__title"><h2>Pair an Android phone</h2><p>Generate a one-time QR code, then scan it in the WealthOS Connect app. The code expires after 10 minutes.</p></div><div className="mobile-connections__pairing"><div><label>Approved SMS senders<textarea value={senders} onChange={event=>setSenders(event.target.value)} rows={4}/></label><small>Only messages from these sender IDs are accepted. You can change the list later.</small><button type="button" disabled={busy||!senderList.length} onClick={()=>void pair()}><QrCode size={16}/>{pairing?'Generate a new QR code':'Generate pairing QR'}</button></div>{pairing&&<div className="mobile-connections__qr">{qr?<img src={qr} alt="WealthOS Connect pairing QR code"/>:<RefreshCw className="is-spinning"/>}<strong>Expires {formatDateTime(pairing.expires_at)}</strong><button type="button" className="is-secondary" onClick={()=>void copySecret()}><Copy size={14}/> Copy manual pairing code</button></div>}</div></section>
    <section className="settings-subpage__panel"><div className="settings-subpage__title"><h2>Connected devices</h2><p>Each phone has a separate token. Revoking one device does not affect your WealthOS password.</p></div><div className="mobile-connections__devices">{devices.length?devices.map(device=><article key={device.id} className={device.status==='ACTIVE'?'is-active':'is-revoked'}><span className="mobile-connections__device-icon"><Smartphone size={20}/></span><div><strong>{device.device_name}</strong><small>{device.os_version??device.platform} · App {device.app_version??'—'}</small><small>Last sync: {device.last_sync_at?formatDateTime(device.last_sync_at):'Not synced yet'}</small></div><em>{device.status==='ACTIVE'?<><CheckCircle2 size={14}/> Active</>:<>Revoked</>}</em><div className="mobile-connections__actions">{device.status==='ACTIVE'&&<button type="button" disabled={busy} onClick={()=>void saveSenders(device)}><ShieldCheck size={14}/> Apply sender list</button>}{device.status==='ACTIVE'&&<button type="button" className="is-danger" disabled={busy} onClick={()=>void revoke(device)}><Trash2 size={14}/> Revoke</button>}</div></article>):<div className="mobile-connections__empty"><Link2 size={22}/><strong>No phone connected</strong><span>Generate a QR code above after installing WealthOS Connect.</span></div>}</div><footer><span className={message.includes('updated')||message.includes('copied')||message.includes('revoked')?'is-success':'is-error'}>{message}</span><Link className="mobile-connections__review" to="/accounting/review-queue">Review imported operations</Link></footer></section>
  </section>
}
