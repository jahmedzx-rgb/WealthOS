import { Moon, Sun } from 'lucide-react'

import { useTheme } from '../../context/ThemeContext'
import { useLanguage } from '../../context/LanguageContext'

export default function ThemeToggle() {
  const {t}=useLanguage()
  const {
    theme,
    toggleTheme,
  } = useTheme()

  return (
    <button
      type="button"
      className="theme-toggle"
      title={t('Switch Theme')}
      aria-label={t('Switch Theme')}
      onClick={toggleTheme}
    >
      {theme === 'light'
        ? <Sun size={16} />
        : <Moon size={16} />}
    </button>
  )
}
