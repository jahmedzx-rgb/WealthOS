import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { getAccountProfile } from '../services/accountService'
import { saveUserProfile } from '../pages/userProfile'
import { useLanguage } from '../context/LanguageContext'

export default function BetaProfileInitializer(){const location=useLocation();const{setLanguage}=useLanguage();useEffect(()=>{const params=new URLSearchParams(location.search);if(params.has('tester')){params.delete('tester');window.history.replaceState({},'',`${location.pathname}${params.size?`?${params}`:''}${location.hash}`)}},[location.pathname,location.search,location.hash]);useEffect(()=>{const languageAtRequest=localStorage.getItem('wealthos-language');getAccountProfile().then(profile=>{saveUserProfile({fullName:profile.full_name,email:profile.email},profile.id);if(localStorage.getItem('wealthos-language')===languageAtRequest)setLanguage(profile.preferred_language)}).catch(()=>{/* Keep the last backend-authenticated cache while temporarily offline. */})},[setLanguage]);return null}
