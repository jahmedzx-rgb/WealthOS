import { Landmark, Sparkles } from 'lucide-react'
import type { FormEvent, ReactNode } from 'react'
import './IncomeOperation.css'
import { useLanguage } from '../context/LanguageContext'

type Props = { title: string; children: ReactNode; preview?: ReactNode; className?: string; onSubmit?: (event: FormEvent<HTMLFormElement>) => void }

export default function OperationForm({ title, children, preview, className='', onSubmit }: Props) {
  const {t}=useLanguage()
  return <div className={`income-operation standard-operation ${className}`.trim()}>
    <form className="income-operation__form standard-operation__form" onSubmit={onSubmit}>
      <div className="income-operation__section-heading">
        <div><span>01</span><div><h3>{t(title)}</h3><p>{t('Enter the transaction details below.')}</p></div></div><Sparkles size={17} />
      </div>
      {children}
    </form>
    <aside className="income-operation__summary">
      <div className="income-operation__summary-header"><span><Landmark size={18} /></span><div><h3>{t('Transaction preview')}</h3><p>{t('Live operation summary')}</p></div></div>
      {preview ?? <><div className="standard-operation__preview"><span>{t(title)}</span><strong>{t('Ready for review')}</strong><small>{t('Values update from the operation details.')}</small></div>
      <div className="income-operation__effects"><h4>{t('Before you execute')}</h4><p><span>{t('Validation')}</span><strong>{t('Automatic')}</strong></p><p><span>{t('Ledger impact')}</span><strong>{t('Balanced')}</strong></p><p><span>{t('Audit trail')}</span><strong>{t('Recorded')}</strong></p></div>
      <div className="income-operation__smart-note"><Sparkles size={16} /><p><strong>{t('WealthOS intelligence')}</strong>{t('Related accounts and assets are checked before posting.')}</p></div></>}
    </aside>
  </div>
}
