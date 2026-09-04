import { ArrowRight, History, ReceiptText } from 'lucide-react'
import { Link } from 'react-router-dom'
import type { FinancialActivity } from '../../services/accountingService'
import { useCurrency } from '../../context/CurrencyContext'
import FormattedMoney from '../ui/FormattedMoney'
import { activityDetail, activityTitle } from '../../utils/activityLabels'
import { formatDate } from '../../utils/dateFormat'
import Card from '../ui/Card'
import './RecentActivity.css'
import { useLanguage } from '../../context/LanguageContext'

export default function RecentActivity({ activities }: { activities: FinancialActivity[] }) {
  const { formatMoney } = useCurrency()
  const {t,direction,language}=useLanguage()
  return <Card icon={History} title="Recent Activity" action={<Link className="recent-activity__view-all" to="/activity">{t('View All')} <ArrowRight size={16} style={direction==='rtl'?{transform:'rotate(180deg)'}:undefined}/></Link>}>
    <div className="recent-activity">
      {activities.slice(0,5).map((activity)=><article key={activity.id} className="recent-activity__item"><div className="recent-activity__icon"><ReceiptText size={18}/></div><div className="recent-activity__content"><div className="recent-activity__row"><strong>{activityTitle(activity,language)}</strong><span className="recent-activity__time">{formatDate(activity.transaction_date)}</span></div><div className="recent-activity__row"><span className="recent-activity__description">{activityDetail(activity,language)}</span>{activity.cash_change!==0&&<span className={activity.cash_change>0?'recent-activity__amount recent-activity__amount--positive':'recent-activity__amount recent-activity__amount--negative'}><FormattedMoney value={formatMoney(activity.cash_change)} sign={activity.cash_change>0?'+':''}/></span>}</div></div></article>)}
      {!activities.length&&<div className="recent-activity__item"><div className="recent-activity__content"><strong>{t('No Posted Activity Yet')}</strong><span className="recent-activity__description">{t('Completed operations will appear here.')}</span></div></div>}
    </div>
  </Card>
}
