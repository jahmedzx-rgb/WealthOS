/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from 'react'
import { getSecurities, type SecurityLookup } from '../services/securityService'

export function useSecurities(){
  const[securities,setSecurities]=useState<SecurityLookup[]>([]);const[loading,setLoading]=useState(true);const[error,setError]=useState('')
  const refresh=useCallback(async()=>{setLoading(true);setError('');try{setSecurities(await getSecurities())}catch(reason){setError(reason instanceof Error?reason.message:'Failed to load securities.')}finally{setLoading(false)}},[])
  useEffect(()=>{void refresh()},[refresh])
  return{securities,loading,error,refresh}
}
