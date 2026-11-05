import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'
import { getAccountProfile } from '../services/accountService'
import { saveUserProfile } from '../pages/userProfile'
import { useLanguage } from '../context/LanguageContext'

export default function BetaProfileInitializer(){const location=useLocation();const{setLanguage}=useLanguage();useEffect(()=>{const params=new URLSearchParams(location.search);if(params.has('tester')){params.delete('tester');window.history.replaceState({},'',`${location.pathname}${params.size?`?${params}`:''}${location.hash}`)}},[location.pathname,location.search,location.hash]);useEffect(()=>{let cancelled=false;getAccountProfile().then(profile=>{if(cancelled)return;saveUserProfile({fullName:profile.full_name,email:profile.email},profile.id);const saved=localStorage.getItem('wealthos-language');if(saved!=='ar'&&saved!=='en')setLanguage(profile.preferred_language)}).catch(()=>{/* Keep the last backend-authenticated cache while temporarily offline. */});return()=>{cancelled=true}},[setLanguage]);return null}
