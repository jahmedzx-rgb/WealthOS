export type UserProfile={fullName:string;email:string}
type StoredUserProfile=UserProfile&{accountId:number;source:'backend'}
const fallback:UserProfile={fullName:'Ahmed',email:'ahmed@example.com'}
export function parseStoredUserProfile(value:string|null):UserProfile|null{try{const parsed=JSON.parse(value??'null') as Partial<StoredUserProfile>|null;if(!parsed||parsed.source!=='backend'||!Number.isInteger(parsed.accountId)||typeof parsed.fullName!=='string'||typeof parsed.email!=='string')return null;return{fullName:parsed.fullName,email:parsed.email}}catch{return null}}
export function loadUserProfile():UserProfile{return parseStoredUserProfile(localStorage.getItem('wealthos-user-profile'))??fallback}
export function saveUserProfile(profile:UserProfile,accountId:number){const stored:StoredUserProfile={...profile,accountId,source:'backend'};localStorage.setItem('wealthos-user-profile',JSON.stringify(stored));window.dispatchEvent(new CustomEvent('wealthos-profile-updated',{detail:profile}))}
