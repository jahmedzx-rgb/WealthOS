import { apiDelete, apiGet, apiPatch, apiPost } from './api'

export type MobileDevice={id:number;public_id:string;device_name:string;platform:string;status:'ACTIVE'|'REVOKED';sender_allowlist:string[];app_version:string|null;os_version:string|null;created_at:string;activated_at:string;last_seen_at:string|null;last_sync_at:string|null;revoked_at:string|null}
export type MobilePairing={pairing_id:string;pairing_secret:string;expires_at:string;sender_allowlist:string[]}

export const getMobileDevices=()=>apiGet<MobileDevice[]>('/mobile/devices')
export const createMobilePairing=(senderAllowlist:string[])=>apiPost<MobilePairing>('/mobile/pairings',{sender_allowlist:senderAllowlist})
export const updateMobileDeviceSenders=(id:number,senderAllowlist:string[])=>apiPatch<MobileDevice>(`/mobile/devices/${id}/senders`,{sender_allowlist:senderAllowlist})
export const revokeMobileDevice=(id:number)=>apiDelete(`/mobile/devices/${id}`)
