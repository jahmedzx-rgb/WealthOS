import { apiGet, apiPost } from './api'

export type FinancialPlatform={id?:number;code:string;name:string;name_ar:string;country:string;website:string;services:string[];description?:string}
export const getFinancialPlatforms=()=>apiGet<FinancialPlatform[]>('/investing/financial-platforms')
export const getFinancialPlatformCatalog=()=>apiGet<FinancialPlatform[]>('/investing/financial-platforms/catalog')
export const createFinancialPlatform=(code:string)=>apiPost<FinancialPlatform>('/investing/financial-platforms',{code})
