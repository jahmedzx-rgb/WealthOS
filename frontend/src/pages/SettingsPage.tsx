import { ChevronRight, Coins, DatabaseBackup, LockKeyhole, Settings, ShieldCheck, UserRound } from 'lucide-react'
import { Link } from 'react-router-dom'
import PageHeader from '../components/ui/PageHeader'
import { loadUserProfile } from './userProfile'
import './SettingsPage.css'
import { useLanguage } from '../context/LanguageContext'

const sections = [
  { to: '/settings/profile', title: 'Profile', copy: 'Manage your name and account email.', icon: UserRound },
  { to: '/settings/security', title: 'Email & Password', copy: 'Update sign-in details and account protection.', icon: LockKeyhole },
  { to: '/settings/currencies', title: 'Currencies', copy: 'Choose reporting and transaction currencies.', icon: Coins },
  { to: '/settings/data-account', title: 'Data & Account', copy: 'Download a backup or permanently delete your account.', icon: DatabaseBackup },
]

export default function SettingsPage() {
  const profile = loadUserProfile()
  const {t}=useLanguage()
  return <section className="settings-page">
    <PageHeader title={t('Settings')} subtitle={t('Manage your account, security, and financial preferences.')} icon={Settings}/>
    <div className="settings-page__metrics"><article><span>{t('Account owner')}</span><strong>{profile.fullName}</strong><small>{profile.email}</small></article><article><span>{t('Account security')}</span><strong>{t('Protected')}</strong><small>{t('Password management available')}</small></article><article><span>{t('Workspace')}</span><strong>{t('Personal')}</strong><small>{t('Private wealth profile')}</small></article></div>
    <section className="settings-page__panel"><div><h2>{t('Settings center')}</h2><p>{t('Select what you want to manage.')}</p></div>{sections.map(item=>{const Icon=item.icon;return <Link to={item.to} key={item.to}><span><Icon size={18}/></span><div><strong>{t(item.title)}</strong><small>{t(item.copy)}</small></div><ChevronRight size={17}/></Link>})}</section>
    <aside className="settings-page__notice"><ShieldCheck size={18}/><div><strong>{t('Privacy First')}</strong><small>{t('Your financial records are owned by your account. You can download a backup or permanently delete them at any time.')}</small></div></aside>
  </section>
}
