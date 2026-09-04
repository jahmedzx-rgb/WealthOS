import { ArrowLeft, ArrowRight, House } from 'lucide-react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'

import Card from '../components/ui/Card'
import { operationEngine } from '../operations/operationEngine'
import { operationRenderer } from '../operations/operationRenderer'
import './OperationWorkspacePage.css'
import './PropertyJourneyTypography.css'
import { useLanguage } from '../context/LanguageContext'


export default function OperationWorkspacePage() {
  const { operation } = useParams()
  const navigate = useNavigate()
  const location = useLocation()
  const {direction,t}=useLanguage()

  function goBack() {
    if (location.key === 'default') {
      navigate('/')
      return
    }
    navigate(-1)
  }
  const config = operation
    ? operationEngine.get(operation)
    : null

  if (!config || !operation) {
    return (
      <div className="page">
        <Card title="Operation">
          <p>{t('Operation not found.')}</p>

          <Link to="/">
            {t('Back to Dashboard')}
          </Link>
        </Card>
      </div>
    )
  }

  const OperationIcon = config.icon
  const BackIcon=direction==='rtl'?ArrowRight:ArrowLeft
  const editingCreditCard=operation==='credit-card-account'&&new URLSearchParams(location.search).has('edit')
  const editingDeposit=operation==='deposit'&&new URLSearchParams(location.search).has('edit')
  const editingProperty=operation==='property'&&new URLSearchParams(location.search).has('edit')
  const query=new URLSearchParams(location.search)
  const propertyJourney=operation==='property'||operation==='property-valuation'||operation==='inheritance'||(operation==='sell-asset'&&query.has('property'))||(operation==='income'&&(query.has('property')||['RENTAL','COMMERCIAL_RENT','SHORT_TERM_RENT'].includes(query.get('type')??'')))||(operation==='expense'&&query.get('type')==='PROPERTY_MAINTENANCE')
  const pageTitle=editingCreditCard?'Edit Credit Card':editingDeposit?'Edit Deposit':editingProperty?'Edit Property':config.title
  const pageDescription=editingCreditCard?'Update the selected card details and settings.':editingDeposit?'Update deposit details or post a balance correction.':editingProperty?'Update property details or post a value correction.':config.description

  return (
    <div className="page">
      <Card className={`operation-workspace operation-workspace--${operation}${propertyJourney?' operation-workspace--property-journey':''}`}>
        <div className="operation-workspace__header">
          <div className="operation-workspace__identity">
            <button className="operation-workspace__back" type="button" onClick={goBack} aria-label={t('Back to previous page')} title={t('Back')}><BackIcon size={18}/></button>
            <Link className="operation-workspace__home" to="/" aria-label={t('Home')} title={t('Home')}><House size={17}/></Link>
            <span className="operation-workspace__page-icon"><OperationIcon size={18}/></span>
            <div><h2>{t(pageTitle)}</h2><p>{t(pageDescription)}</p></div>
          </div>
          <div className="operation-workspace__header-actions" id={operation === 'income' ? 'income-operation-header-actions' : operation === 'expense' ? 'expense-operation-header-actions' : undefined}/>
        </div>

        {operationRenderer(operation)}
      </Card>
    </div>
  )
}
