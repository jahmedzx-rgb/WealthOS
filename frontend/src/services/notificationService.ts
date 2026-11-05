import { apiGet, apiPost } from './api'

export type DistributionReminder={announcement_id?:number;position_id:number;security_id:number;symbol:string;name:string;portfolio_id:number;portfolio_name:string;announcement_date?:string|null;eligibility_date?:string;distribution_date:string;payment_date?:string;amount_per_unit?:number;eligible_quantity?:number;expected_amount:number|null;frequency:string|null;withholding_tax_rate:number;expected_tax_amount:number|null;expected_net_amount:number|null;currency_code:string;source?:string;status?:string;days_until:number}
export const getDistributionReminders=(days=7,includeOverdue=false)=>apiGet<DistributionReminder[]>(`/investing/distribution-reminders?days=${days}&include_overdue=${includeOverdue}`)
export const syncDistributionAnnouncements=()=>apiPost<{positions_checked:number;created:number;updated:number;sources_checked:string[]}>('/investing/distribution-announcements/sync',{})
