import { type FormEvent, type ReactNode, useEffect, useState } from 'react'
import { Eye, EyeOff } from 'lucide-react'
import { useLanguage } from '../context/LanguageContext'
import SetupGate from './SetupGate'
import wealthosIcon from '../../../assets/branding/wealthos-app-icon.svg'

const API = '/api/v1'

export default function BootstrapGate({ children }: { children: ReactNode }) {
  const { direction } = useLanguage()
  const [mode, setMode] = useState<'loading' | 'local' | 'auth' | 'ready' | 'error'>('loading')
  const [authMode, setAuthMode] = useState<'login' | 'register' | 'recover'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [inviteCode, setInviteCode] = useState('')
  const [recoveryCode, setRecoveryCode] = useState('')
  const [replacementCode, setReplacementCode] = useState('')
  const [locale, setLocale] = useState<'ar' | 'en'>(direction === 'rtl' ? 'ar' : 'en')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const probe = () => {
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 12000)
    return fetch(`${API}/account/me`, { credentials: 'same-origin', signal: controller.signal }).then(response => {
      if (response.ok) setMode('ready')
      else if (response.status === 401) setMode('auth')
      else if (response.status === 423) setMode('local')
      else setMode('error')
    }).catch(() => setMode('error')).finally(() => window.clearTimeout(timeout))
  }

  useEffect(() => { probe() }, [])

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submitting) return
    setSubmitting(true)
    setError('')
    const controller = new AbortController()
    const timeout = window.setTimeout(() => controller.abort(), 15_000)
    try {
      const endpoint = authMode === 'register' ? 'register' : authMode === 'recover' ? 'recover' : 'login'
      const requestBody = authMode === 'register'
        ? { username, password, locale, invite_code: inviteCode }
        : authMode === 'recover'
          ? { username, recovery_code: recoveryCode, new_password: password }
          : { username, password }
      const response = await fetch(`${API}/auth/${endpoint}`, {
        method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json' }, signal: controller.signal,
        body: JSON.stringify(requestBody),
      })
      if (response.ok) {
        if (authMode === 'recover') {
          const payload = await response.json() as { recovery_code: string }
          setReplacementCode(payload.recovery_code)
          return
        }
        await probe(); return
      }
      const payload = await response.json().catch(() => null) as { detail?: { key?: string } } | null
      const key = payload?.detail?.key
      const messages: Record<string, string> = direction === 'rtl'
        ? { 'auth.invalid_credentials': 'اسم المستخدم أو كلمة المرور غير صحيحة.', 'auth.recovery_invalid': 'اسم المستخدم أو رمز الاسترداد غير صحيح.', 'auth.username_taken': 'اسم المستخدم مستخدم بالفعل.', 'auth.registration_full': 'اكتمل عدد حسابات النسخة التجريبية.', 'auth.invite_invalid': 'رمز الدعوة غير صحيح أو مستخدم.', 'auth.password_weak': 'اختر كلمة مرور أقوى من 12 حرفًا على الأقل.' }
        : { 'auth.invalid_credentials': 'The username or password is incorrect.', 'auth.recovery_invalid': 'The username or recovery code is incorrect.', 'auth.username_taken': 'That username is already in use.', 'auth.registration_full': 'The beta account limit has been reached.', 'auth.invite_invalid': 'The invite code is invalid or already used.', 'auth.password_weak': 'Choose a stronger password with at least 12 characters.' }
      setError(messages[key ?? ''] ?? (direction === 'rtl' ? 'تعذر إكمال الطلب.' : 'Unable to complete the request.'))
    } catch {
      setError(direction === 'rtl' ? 'انتهت مهلة الاتصال. تحقق من النتيجة قبل إعادة المحاولة.' : 'The connection timed out. Check the result before trying again.')
    } finally {
      window.clearTimeout(timeout)
      setSubmitting(false)
    }
  }

  if (mode === 'local') return <SetupGate>{children}</SetupGate>
  if (mode === 'ready') return children
  if (mode === 'loading') return <div className="app-route-loading">{direction === 'rtl' ? 'جارٍ تحضير WealthOS…' : 'Preparing WealthOS…'}</div>
  if (mode === 'error') return <div className="app-route-loading">{direction === 'rtl' ? 'الخدمة لا تستجيب.' : 'The service is not responding.'}<button type="button" onClick={() => { setMode('loading'); void probe() }} style={{ display: 'block', margin: '12px auto' }}>{direction === 'rtl' ? 'إعادة المحاولة' : 'Retry'}</button></div>

  if (replacementCode) return <main className="setup-wizard" dir={direction}><section className="setup-wizard__card"><header><img className="setup-wizard__brand" src={wealthosIcon} alt="WealthOS"/><div><small>PRIVATE WEALTH WORKSPACE</small><h1>{direction === 'rtl' ? 'احفظ رمز الاسترداد الجديد' : 'Save your new recovery code'}</h1></div></header><div className="setup-wizard__body"><p>{direction === 'rtl' ? 'يظهر هذا الرمز مرة واحدة. احفظه في مكان آمن لاستخدامه إذا نسيت كلمة المرور مرة أخرى.' : 'This code is shown once. Store it safely so you can recover the account again.'}</p><div className="setup-wizard__notice"><strong dir="ltr">{replacementCode}</strong></div></div><footer><button type="button" onClick={() => void probe()}>{direction === 'rtl' ? 'حفظته، المتابعة' : 'I saved it, continue'}</button></footer></section></main>

  const authTitle = authMode === 'register' ? (direction === 'rtl' ? 'إنشاء حساب' : 'Create account') : authMode === 'recover' ? (direction === 'rtl' ? 'استعادة الحساب' : 'Recover account') : (direction === 'rtl' ? 'تسجيل الدخول' : 'Sign in')
  return <main className="setup-wizard" dir={direction}><form className="setup-wizard__card" onSubmit={submit}>
    <header><img className="setup-wizard__brand" src={wealthosIcon} alt="WealthOS"/><div><small>WEB BETA</small><h1>{authTitle}</h1></div></header>
    <div className="setup-wizard__body">
      <label>{direction === 'rtl' ? 'اسم المستخدم' : 'Username'}<input autoComplete="username" value={username} onChange={event => setUsername(event.target.value)} required minLength={3}/></label>
      {authMode === 'recover' && <label>{direction === 'rtl' ? 'رمز الاسترداد' : 'Recovery code'}<input dir="ltr" autoComplete="off" value={recoveryCode} onChange={event => setRecoveryCode(event.target.value)} required minLength={32} maxLength={80}/></label>}
      <label>{authMode === 'recover' ? (direction === 'rtl' ? 'كلمة المرور الجديدة' : 'New password') : (direction === 'rtl' ? 'كلمة المرور' : 'Password')}<span className="setup-wizard__password"><input type={showPassword ? 'text' : 'password'} autoComplete={authMode === 'login' ? 'current-password' : 'new-password'} value={password} onChange={event => setPassword(event.target.value)} required minLength={12}/><button type="button" onClick={() => setShowPassword(value => !value)} aria-label={showPassword ? (direction === 'rtl' ? 'إخفاء كلمة المرور' : 'Hide password') : (direction === 'rtl' ? 'إظهار كلمة المرور' : 'Show password')}>{showPassword ? <EyeOff size={16}/> : <Eye size={16}/>}</button></span></label>
      {authMode === 'register' && <label>{direction === 'rtl' ? 'اللغة' : 'Language'}<select value={locale} onChange={event => setLocale(event.target.value as 'ar' | 'en')}><option value="ar">العربية</option><option value="en">English</option></select></label>}
      {authMode === 'register' && <label>Invite code<input type="password" autoComplete="off" value={inviteCode} onChange={event => setInviteCode(event.target.value)} required minLength={16}/></label>}
      {authMode === 'login' && <button className="setup-wizard__text-action" type="button" onClick={() => { setAuthMode('recover'); setError(''); setPassword(''); setShowPassword(false) }}>{direction === 'rtl' ? 'نسيت كلمة المرور؟' : 'Forgot password?'}</button>}
      {error && <p className="setup-wizard__error">{error}</p>}
    </div>
    <footer><button type="button" disabled={submitting} className="secondary" onClick={() => { setAuthMode(authMode === 'login' ? 'register' : 'login'); setError(''); setPassword(''); setRecoveryCode(''); setShowPassword(false) }}>{authMode === 'login' ? (direction === 'rtl' ? 'إنشاء حساب' : 'Create account') : (direction === 'rtl' ? 'العودة لتسجيل الدخول' : 'Back to sign in')}</button><button type="submit" disabled={submitting}>{submitting ? (direction === 'rtl' ? 'جارٍ الاتصال…' : 'Connecting…') : authMode === 'register' ? (direction === 'rtl' ? 'إنشاء' : 'Create') : authMode === 'recover' ? (direction === 'rtl' ? 'إعادة تعيين كلمة المرور' : 'Reset password') : (direction === 'rtl' ? 'دخول' : 'Sign in')}</button></footer>
  </form></main>
}
