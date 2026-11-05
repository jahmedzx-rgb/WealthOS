import type { ReactNode } from 'react'

import './Card.css'
import { useLanguage } from '../../context/LanguageContext'
import type { LucideIcon } from 'lucide-react'

type Props = {
  children: ReactNode
  title?: string
  titleNode?: ReactNode
  subtitle?: string
  action?: ReactNode
  className?: string
  icon?: LucideIcon
}

export default function Card({
  children,
  title,
  titleNode,
  subtitle,
  action,
  className,
  icon: Icon,
}: Props) {
  const {t}=useLanguage()
  return (
    <section
      className={[
        'card',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {(title || titleNode || subtitle || action) && (
        <header className="card__header">
          <div>
            {(title || titleNode) && <div className="card__title-row">{Icon&&<span className="card__title-icon"><Icon size={15}/></span>}<h3 className="card__title">{titleNode??t(title!)}</h3></div>}

            {subtitle && (
              <p className="card__subtitle">
                {t(subtitle)}
              </p>
            )}
          </div>

          {action && (
            <div className="card__action">
              {action}
            </div>
          )}
        </header>
      )}

      <div className="card__content">
        {children}
      </div>
    </section>
  )
}
