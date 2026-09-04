import { ArrowLeft, ArrowRight, House } from 'lucide-react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useLanguage } from '../../context/LanguageContext'
import './PageNavigation.css'
import './PageNavigationGold.css'
import './PageNavigationTypography.css'
import './PageNavigationPlacement.css'
export default function PageNavigation(){const navigate=useNavigate();const location=useLocation();const {direction,t}=useLanguage();const home=location.pathname==='/';const goBack=()=>location.key==='default'?navigate('/'):navigate(-1);const BackIcon=direction==='rtl'?ArrowRight:ArrowLeft;return <nav className="page-navigation" aria-label={t('Page navigation')}><button type="button" onClick={goBack} disabled={home} aria-label={t('Back')} title={t('Back')}><BackIcon size={18}/></button><Link className={home?'is-active':''} to="/" aria-label={t('Home')} title={t('Home')}><House size={17}/></Link></nav>}
