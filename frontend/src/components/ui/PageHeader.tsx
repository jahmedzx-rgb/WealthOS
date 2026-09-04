import type { ElementType, ReactNode } from 'react'

import PageNavigation from './PageNavigation'
import { useLanguage } from '../../context/LanguageContext'
import './PageHeader.css'
import './PageHeaderSizing.css'

type PageHeaderProps = { title: string; subtitle: string; icon: ElementType; eyebrow?: string; actions?: ReactNode; className?: string; hideNavigation?: boolean }

export default function PageHeader({ title, subtitle, icon: Icon, eyebrow, actions, className = '', hideNavigation = false }: PageHeaderProps) {
  const {t}=useLanguage()
  return <header className={`page-header ${hideNavigation ? 'page-header--without-navigation' : ''} ${className}`.trim()}>
    {!hideNavigation && <PageNavigation />}
    <div className="page-header__identity"><span className="page-header__icon"><Icon size={18}/></span><div>{eyebrow && <p>{t(eyebrow)}</p>}<h1>{t(title)}</h1><small>{t(subtitle)}</small></div></div>
    <div className="page-header__actions">{actions}</div>
  </header>
}
