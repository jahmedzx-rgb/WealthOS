import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { useLanguage } from '../context/LanguageContext'
import SetupGate from './SetupGate'
import wealthosIcon from '../../../assets/branding/wealthos-app-icon.svg'

const API = '/api/v1'

export default function BootstrapGate({ children }: { children: ReactNode }) {
  const { direction } = useLanguage()
  const [mode, setMode] = useState<'loading' | 'local' | 'auth' | 'ready' | 'error'>('loading')
  const [registering, setRegistering] = useState(false)
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [locale, setLocale] = useState<'ar' | 'en'>(direction === 'rtl' ? 'ar' : 'en')
  const [error, setError] = useState('')

  const probe = () => fetch(`${API}/account/me`, { credentials: 'same-origin' }).then(response => {
    if (response.ok) setMode('ready')
    else if (response.status === 401) setMode('auth')
    else if (response.status === 423) setMode('local')
    else setMode('error')
  }).catch(() => setMode('error'))

  useEffect(() => { probe() }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError('')
    const response = await fetch(`${API}/auth/${registering ? 'register' : 'login'}`, {
      method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(registering ? { username, password, locale } : { username, password }),
    })
    if (response.ok) return probe()
    const payload = await response.json().catch(() => null) as { detail?: { key?: string } } | null
    const key = payload?.detail?.key
    const messages: Record<string, string> = direction === 'rtl'
      ? { 'auth.invalid_credentials': 'اسم المستخدم أو كلمة المرور غير صحيحة.', 'auth.username_taken': 'اسم المستخدم مستخدم بالفعل.', 'auth.registration_full': 'اكتمل عدد حسابات النسخة التجريبية.', 'auth.password_weak': 'اختر كلمة مرور أقوى من 12 حرفًا على الأقل.' }
      : { 'auth.invalid_credentials': 'The username or password is incorrect.', 'auth.username_taken': 'That username is already in use.', 'auth.registration_full': 'The beta account limit has been reached.', 'auth.password_weak': 'Choose a stronger password with at least 12 characters.' }
    setError(messages[key ?? ''] ?? (direction === 'rtl' ? 'تعذر إكمال الطلب.' : 'Unable to complete the request.'))
  }

  if (mode === 'local') return <SetupGate>{children}</SetupGate>
  if (mode === 'ready') return children
  if (mode === 'loading') return <div className="app-route-loading">{direction === 'rtl' ? 'جارٍ تحضير WealthOS…' : 'Preparing WealthOS…'}</div>
  if (mode === 'error') return <div className="app-route-loading">{direction === 'rtl' ? 'تعذر الاتصال بالخدمة.' : 'Unable to connect to the service.'}</div>

  return <main className="setup-wizard" dir={direction}><form className="setup-wizard__card" onSubmit={submit}>
    <header><img className="setup-wizard__brand" src={wealthosIcon} alt="WealthOS"/><div><small>WEB BETA</small><h1>{registering ? (direction === 'rtl' ? 'إنشاء حساب' : 'Create account') : (direction === 'rtl' ? 'تسجيل الدخول' : 'Sign in')}</h1></div></header>
    <div className="setup-wizard__body">
      <label>{direction === 'rtl' ? 'اسم المستخدم' : 'Username'}<input autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required minLength={3}/></label>
      <label>{direction === 'rtl' ? 'كلمة المرور' : 'Password'}<input type="password" autoComplete={registering ? 'new-password' : 'current-password'} value={password} onChange={event => setPassword(event.target.value)} required minLength={12}/></label>
      {registering && <label>{direction === 'rtl' ? 'اللغة' : 'Language'}<select value={locale} onChange={event => setLocale(event.target.value as 'ar' | 'en')}><option value="ar">العربية</option><option value="en">English</option></select></label>}
      {error && <p className="setup-wizard__error">{error}</p>}
    </div>
    <footer><button type="button" className="secondary" onClick={() => { setRegistering(!registering); setError('') }}>{registering ? (direction === 'rtl' ? 'لدي حساب' : 'I have an account') : (direction === 'rtl' ? 'إنشاء حساب' : 'Create account')}</button><button type="submit">{registering ? (direction === 'rtl' ? 'إنشاء' : 'Create') : (direction === 'rtl' ? 'دخول' : 'Sign in')}</button></footer>
  </form></main>
}
