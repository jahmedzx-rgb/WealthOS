import { useState, type ReactNode } from 'react'
import { Landmark } from 'lucide-react'
import './BankIdentity.css'

const banks: [string, string[]][] = [
  ['neo', ['neo', 'neo bank', 'neo digital bank', 'نيو', 'بنك نيو']],
  ['amex', ['amex', 'amex saudi', 'amex saudi arabia', 'american express', 'american express saudi arabia', 'american express saudi', 'أميكس', 'اميكس', 'أميكس السعودية', 'اميكس السعودية', 'أمريكان إكسبريس', 'امريكان اكسبريس', 'أمريكان إكسبريس السعودية', 'امريكان اكسبريس السعودية']],
  ['bsf', ['bsf', 'banque saudi fransi', 'saudi fransi bank', 'saudi french bank', 'البنك الفرنسي', 'البنك السعودي الفرنسي', 'السعودي الفرنسي', 'الفرنسي']],
  ['enbd', ['enbd', 'enbd x', 'emirates nbd', 'emirates nbd bank', 'الإمارات دبي الوطني', 'الامارات دبي الوطني', 'بنك الإمارات دبي الوطني', 'بنك الامارات دبي الوطني']],
  ['stc', ['stc', 'stc bank', 'stcbank', 'بنك stc', 'بنك إس تي سي', 'بنك اس تي سي', 'إس تي سي بنك', 'اس تي سي بنك']],
  ['jazira', ['ajb', 'baj', 'bank aljazira', 'bank al jazira', 'aljazira bank', 'al jazira bank', 'aljazira', 'الجزيرة', 'بنك الجزيرة']],
  ['anb', ['anb', 'arab national bank', 'arab bank', 'البنك العربي', 'العربي', 'البنك العربي الوطني']],
  ['d360', ['d360', 'd360 bank', 'd360bank', 'دي 360', 'بنك d360', 'بنك دي 360']],
  ['snb', ['snb', 'ncb', 'alahli', 'al ahli', 'saudi national bank', 'الأهلي', 'الاهلي', 'البنك الأهلي', 'البنك الاهلي', 'البنك الأهلي السعودي']],
  ['rajhi', ['alrajhi', 'al rajhi', 'al rajhi bank', 'alrajhi bank', 'الراجحي', 'مصرف الراجحي']],
  ['riyad', ['riyad', 'riyad bank', 'الرياض', 'بنك الرياض']],
  ['alinma', ['alinma', 'alinma bank', 'الإنماء', 'الانماء', 'مصرف الإنماء', 'مصرف الانماء']],
  ['sab', ['sab', 'sabb', 'saudi awwal bank', 'الأول', 'الاول', 'ساب', 'البنك السعودي الأول']],
  ['bilad', ['bank albilad', 'albilad', 'al bilad', 'البلاد', 'بنك البلاد']],
]

export function bankIdentityKey(bank:string){
  const normalized=bank.trim().toLowerCase().replace(/[-_]+/g,' ').replace(/\s+/g,' ')
  return banks.find(([,aliases])=>aliases.includes(normalized))?.[0]??normalized
}

export default function BankIdentity({ bank, children }: { bank: string; children?: ReactNode }) {
  const key = bankIdentityKey(bank)
  const knownBank = banks.some(([candidate]) => candidate === key)
  const [failed, setFailed] = useState<string>()
  const iconClass=key==='jazira'?' bank-identity__icon--jazira':key==='neo'?' bank-identity__icon--neo':''
  const iconSource=key==='jazira'?'/banks/jazira-symbol.svg':key==='neo'?'/banks/neo-app.jpg':`/banks/${key}.${key === 'enbd' || key === 'bsf' ? 'png' : 'ico'}`
  return <span className="bank-identity"><span className={`bank-identity__icon${key && failed !== key ? iconClass : ''}`} aria-hidden="true">
    {knownBank && failed !== key ? <img src={iconSource} alt="" width={24} height={24} onError={() => setFailed(key)}/> : <Landmark size={20}/>}
  </span><span className="bank-identity__name">{children ?? bank}</span></span>
}
