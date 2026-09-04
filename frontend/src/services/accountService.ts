import { apiDelete, apiGet, apiPatch, apiPost } from './api'

export type AccountProfile={id:number;email:string;full_name:string;created_at:string;preferred_language:'ar'|'en';nationality:string|null;country_of_residence:string|null;tax_residence:string|null;investor_type:'INDIVIDUAL'|'ENTITY';default_dividend_withholding_tax_rate:number}
export const getAccountProfile=()=>apiGet<AccountProfile>('/account/me')
export const updateAccountProfile=(profile:Omit<AccountProfile,'id'|'created_at'|'preferred_language'>)=>apiPatch<AccountProfile>('/account/me',profile)
export const getAccountBackup=()=>apiGet<Record<string,unknown>>('/account/backup')
export const deleteAccount=(email:string)=>apiDelete(`/account?confirm_email=${encodeURIComponent(email)}`)
export type AccountPreferences={quick_action_ids:string[]|null}
export const getAccountPreferences=()=>apiGet<AccountPreferences>('/account/preferences')
export const updateAccountPreferences=(quick_action_ids:string[])=>apiPatch<AccountPreferences>('/account/preferences',{quick_action_ids})
export const updatePreferredLanguage=(preferred_language:'ar'|'en')=>apiPatch<{preferred_language:'ar'|'en'}>('/account/preferences/language',{preferred_language})
export type SetupStatus={completed:boolean;has_existing_data:boolean;legacy_data_found:boolean;requires_unlock:boolean;unlocked:boolean;profile:{id:number;full_name:string;email:string}|null}
export type SetupRequest={full_name:string;email:string;local_password:string|null;preferred_language:'ar'|'en';base_currency_code:string;enabled_currency_codes:string[];nationality:string|null;country_of_residence:string|null;tax_residence:string|null;investor_type:'INDIVIDUAL'|'ENTITY';local_data_acknowledged:boolean;existing_data_choice:'RESUME_EXISTING'|'START_CLEAN'|'REVIEW_MIGRATION'|null}
export const getSetupStatus=()=>apiGet<SetupStatus>('/account/setup-status')
export type SetupResult={completed:boolean;profile:{id:number;full_name:string;email:string};recovery_code:string|null}
export const completeSetup=(request:SetupRequest)=>apiPost<SetupResult>('/account/setup',request)
export const unlockLocalAccount=(local_password:string)=>apiPost<{unlocked:boolean}>('/account/unlock',{local_password})
export const lockLocalAccount=()=>apiPost<{locked:boolean}>('/account/lock',{})
export const recoverLocalAccount=(recovery_code:string,new_local_password:string)=>apiPost<{recovered:boolean;recovery_code:string}>('/account/recover',{recovery_code,new_local_password})
export const changeLocalPassword=(current_local_password:string,new_local_password:string)=>apiPost<{changed:boolean;recovery_code:string}>('/account/password/change',{current_local_password,new_local_password})
export const disableLocalPassword=(current_local_password:string)=>apiPost<{disabled:boolean}>('/account/password/disable',{current_local_password})
export const registerWebAccount=(username:string,password:string,locale:'ar'|'en',inviteCode:string)=>apiPost<{id:number;username:string;locale:'ar'|'en'}>('/auth/register',{username,password,locale,invite_code:inviteCode})
export const loginWebAccount=(username:string,password:string)=>apiPost<{id:number;username:string;locale:'ar'|'en'}>('/auth/login',{username,password})
