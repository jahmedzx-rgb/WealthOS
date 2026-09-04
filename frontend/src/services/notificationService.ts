import { apiGet } from './api'

export type DistributionReminder={position_id:number;security_id:number;symbol:string;name:string;portfolio_id:number;portfolio_name:string;distribution_date:string;expected_amount:number|null;frequency:string|null;withholding_tax_rate:number;expected_tax_amount:number|null;expected_net_amount:number|null;currency_code:string;days_until:number}
export const getDistributionReminders=(days=7,includeOverdue=false)=>apiGet<DistributionReminder[]>(`/investing/distribution-reminders?days=${days}&include_overdue=${includeOverdue}`)
