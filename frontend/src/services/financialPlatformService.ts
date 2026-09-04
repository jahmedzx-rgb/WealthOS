import { apiGet } from './api'

export type FinancialPlatform={code:string;name:string;name_ar:string;country:string;website:string;services:string[];description:string}
export const getFinancialPlatforms=()=>apiGet<FinancialPlatform[]>('/investing/financial-platforms')
