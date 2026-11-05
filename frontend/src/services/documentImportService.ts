import { Workbook } from 'exceljs'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist/legacy/build/pdf.mjs'
import pdfWorker from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'
import { recognize } from 'tesseract.js'

GlobalWorkerOptions.workerSrc = pdfWorker

export type ExtractedOperation = { id:string; type:'Income'|'Expense'|'Transfer'|'Card payment'|'Trade'|'Deposit'|'Property'|'Unclassified'; description:string; amount:number|null; currency:string|null; date:string|null; cardLast4:string|null; confidence:number; sourceText:string }
export type DocumentAnalysis = { operations:ExtractedOperation[]; extractedText:string; warnings:string[] }
export const SUPPORTED_FINANCIAL_DOCUMENT_ACCEPT='.pdf,.png,.jpg,.jpeg,.webp,.xlsx,.xlsm,.xls,.csv,.xml'

const arabicDigits:Record<string,string>={'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9','٫':'.','٬':','}
const normalizeDigits=(value:string)=>value.replace(/[٠-٩٫٬]/g,(character)=>arabicDigits[character]??character)
const explicitAmountPattern=/(?:amount|المبلغ|مبلغ|بمبلغ|قيمة)\s*(?:(?:is|of)\s*)?(?::\s*)?(?:(?:SAR|ر\.?س|USD|EUR|GBP|AED|JPY|\$|€|£|⃁)\s*)?([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)(?:\s*(?:SAR|ر\.?س|USD|EUR|GBP|AED|JPY|\$|€|£|⃁))?/giu
const currencyAmountPattern=/(?:SAR|ر\.؟س|USD|EUR|GBP|AED|JPY|\$|€|£|⃁)\s*([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)|([-+]?\s*\d[\d,]*(?:\.\d{1,2})?)\s*(?:SAR|ر\.؟س|USD|EUR|GBP|AED|JPY|\$|€|£|⃁)/gi
const datePattern=/\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})(?:[T ]\d{1,2}:\d{2}(?::\d{2})?)?\b/

function classify(text:string):ExtractedOperation['type']{
  const value=text.toLocaleLowerCase()
  if(/credit\s*limit|حدك\s+الائتماني|الحد\s+الائتماني|استخدام\s+\d+\s*%/.test(value))return'Unclassified'
  // Refund and reversal messages need pairing with their original purchase before posting.
  if(/reversal|reversed|refund|عكس\s+شراء/.test(value))return'Unclassified'
  if(/cashback|استرداد\s+نقدي|استرجاع\s+نقدي/.test(value))return'Income'
  if(/term deposit|fixed deposit|وديعة|مرابحة/.test(value))return'Deposit'
  if(/property purchase|real estate purchase|شراء عقار|شراء منزل|شراء أرض/.test(value))return'Property'
  if(/credit\s*card\s*(?:payment|bill|settlement)|card\s*(?:bill|settlement)|payment\s+to\s+(?:a\s+)?credit\s+card|سداد[^|]{0,40}بطاقة|بطاقة[^|]{0,40}سداد|تأكيد\s+السداد/.test(value))return'Card payment'
  if(/transfer|تحويل|حوالة|حواله/.test(value))return'Transfer'
  if(/trade|shares?|stocks?|securit(?:y|ies)|equity|broker|شراء\s+(?:أسهم|سهم|وحدات)|بيع\s+(?:أسهم|سهم|وحدات)|تداول|أسهم|سهم/.test(value))return'Trade'
  if(/dividend|salary|income|deposit interest|rent|توزيع|راتب|دخل|فائدة|ايجار|إيجار|إيداع|ايداع/.test(value))return'Income'
  if(/point of sale|\bpos\b|mada|مدى|نقاط البيع|شراء عن طريق نقاط البيع|payment|purchase|شراء|fee|withdraw|expense|فاتورة|مشتريات|رسوم|سحب|مصروف|خصم/.test(value))return'Expense'
  return'Unclassified'
}
function currencyFrom(text:string){if(/SAR|ر\.؟س|⃁/i.test(text))return'SAR';if(/USD|\$/i.test(text))return'USD';if(/EUR|€/i.test(text))return'EUR';if(/GBP|£/i.test(text))return'GBP';if(/AED/i.test(text))return'AED';if(/JPY/i.test(text))return'JPY';return null}
function numberFromCell(value:string){const normalized=normalizeDigits(value).replace(/,/g,'').trim();if(!/^[-+]?\d+(?:\.\d{1,2})?$/.test(normalized))return null;const parsed=Number(normalized);return Number.isFinite(parsed)?parsed:null}
function statementAmountFrom(text:string,type:ExtractedOperation['type'],date:string|null){if(!date||type==='Unclassified'||!text.includes('|'))return null;const monetaryCells=text.split('|').map(cell=>numberFromCell(cell)).filter((value):value is number=>value!==null);return monetaryCells.length>=2?monetaryCells[monetaryCells.length-2]:null}
function amountFrom(text:string,cardLast4:string|null){
  let value=normalizeDigits(text).replace(new RegExp(datePattern.source,'giu'),' ')
  value=value.replace(/(?:account|card|حساب|بطاقة)[^\n|]{0,28}?(?:[*x•]+\s*)\d{2,4}\b/giu,' ')
  if(cardLast4)value=value.replace(new RegExp(`(?:[*x•]+\\s*|ending\\s+in\\s+|تنتهي\\s*(?:بـ|ب)?\\s*|رقم\\s*)?${cardLast4}\\b`,'iu'),' ')
  const parse=(token:string|null|undefined)=>{if(!token)return null;const parsed=Number(normalizeDigits(token).replace(/[^\d.-]/g,''));return Number.isFinite(parsed)?parsed:null}
  const labeled=[...value.matchAll(explicitAmountPattern)].map((match)=>parse(match[1])).filter((amount):amount is number=>amount!==null)
  if(labeled.length===1)return labeled[0]
  if(labeled.length>1)return null
  const withoutBalances=value.replace(/(?:available\s+balance|balance|credit\s+limit|رصيد|الصرف\s+المتبقي|حدك\s+الائتماني|الحد\s+الائتماني)[^|]*/giu,' ')
  const currencyMarked=[...withoutBalances.matchAll(currencyAmountPattern)].map((match)=>parse(match[1]??match[2])).filter((amount):amount is number=>amount!==null)
  return currencyMarked.length===1?currencyMarked[0]:null
}
function cardLast4From(text:string){const value=normalizeDigits(text);const match=value.match(/(?:visa|mastercard|mada|card|بطاقة|مدى)[^\n]{0,45}?(?:\*+|x+|•+|ending\s+in|تنتهي\s*(?:بـ|ب)?|رقم\s*)?\s*(\d{4})\b/i);return match?.[1]??null}
export function operationsFromLines(lines:string[]):ExtractedOperation[]{return lines.map((line)=>normalizeDigits(line).replace(/\s+/g,' ').trim()).filter((line)=>line.length>2).map((line,index)=>{if(/(?:رصيد\s*(?:الافتتاح|الافتتاحي|الختام|الختامي)|opening\s+balance|closing\s+balance)/iu.test(line))return null;const cardLast4=cardLast4From(line);const type=classify(line);const date=line.match(datePattern)?.[0]??null;const smsEnvelope=/^\d{4}[-/]\d{1,2}[-/]\d{1,2}[ T]\d{1,2}:\d{2}\s*\|\s*[^|]+\s*\|/u.test(line);const amount=(!smsEnvelope?statementAmountFrom(line,type,date):null)??amountFrom(line,cardLast4);if(type==='Unclassified'&&amount===null)return null;const signals=Number(amount!==null)+Number(type!=='Unclassified')+Number(date!==null)+Number(cardLast4!==null);return{id:`extracted-${index}`,type,description:line.length>110?`${line.slice(0,107)}…`:line,amount,currency:currencyFrom(line),date,cardLast4,confidence:Math.min(96,45+signals*14),sourceText:line} satisfies ExtractedOperation}).filter((item):item is ExtractedOperation=>item!==null).slice(0,500)}

function spreadsheetLines(workbook:Workbook){const lines:string[]=[];workbook.eachSheet((sheet)=>sheet.eachRow((row)=>{const values=(row.values as unknown[]).slice(1).map((value)=>{if(value&&typeof value==='object'&&'text'in value)return String((value as{text:unknown}).text);if(value instanceof Date)return value.toISOString().slice(0,10);return String(value??'')});if(values.some(Boolean))lines.push(values.join(' | '))}));return lines}
async function legacyBinarySpreadsheetLines(buffer:ArrayBuffer){
  const{read:readWorkbook,utils:sheetUtils}=await import('xlsx')
  const workbook=readWorkbook(buffer,{type:'array',cellDates:true})
  const lines:string[]=[]
  for(const sheetName of workbook.SheetNames){
    const rows=sheetUtils.sheet_to_json<unknown[]>(workbook.Sheets[sheetName],{header:1,raw:false,defval:''})
    for(const row of rows){const values=row.map(value=>String(value??'').trim());if(values.some(Boolean))lines.push(values.join(' | '))}
  }
  return lines
}
const startsWithBytes=(bytes:Uint8Array,signature:number[])=>signature.every((value,index)=>bytes[index]===value)
function decodeLegacySpreadsheet(bytes:Uint8Array){
  if(startsWithBytes(bytes,[0xff,0xfe]))return new TextDecoder('utf-16le').decode(bytes)
  if(startsWithBytes(bytes,[0xfe,0xff])){const swapped=new Uint8Array(bytes.length-2);for(let i=2;i+1<bytes.length;i+=2){swapped[i-2]=bytes[i+1];swapped[i-1]=bytes[i]}return new TextDecoder('utf-16le').decode(swapped)}
  const utf8=new TextDecoder('utf-8').decode(bytes)
  if(!utf8.includes('\uFFFD'))return utf8
  try{return new TextDecoder('windows-1256').decode(bytes)}catch{return utf8}
}
function linesFromMarkup(text:string){
  const document=new DOMParser().parseFromString(text,'text/html')
  const tableRows=[...document.querySelectorAll('tr')].map(row=>[...row.querySelectorAll('th,td')].map(cell=>(cell.textContent??'').replace(/\s+/g,' ').trim()).filter(Boolean).join(' | ')).filter(Boolean)
  if(tableRows.length)return tableRows
  const xml=new DOMParser().parseFromString(text,'application/xml')
  const messages=[...xml.querySelectorAll('sms')]
  if(messages.length){
    const now=new Date()
    const cutoffDate=new Date(now.getFullYear(),now.getMonth(),now.getDate())
    cutoffDate.setDate(cutoffDate.getDate()-8)
    const cutoff=cutoffDate.getTime()
    const financialMessage=/transaction|purchase|payment|card|credit|debit|transfer|deposit|withdraw|balance|amount|sar|\br\.s\b|\$|عملية|شراء|دفع|سداد|بطاقة|ائتمان|مدى|حوالة|تحويل|إيداع|ايداع|سحب|رصيد|مبلغ|خصم|مشتريات|رسوم|راتب|توزيع|استلام/i
    const verificationMessage=/otp|verification code|one.time password|رمز التحقق|رمز التأكيد|رمز لمرة واحدة|رمز\s+(?:التفعيل|التنشيط)/i
    const creditLimitNotice=/(?:\b\d{1,3}\s*%\s*(?:of\s+)?(?:your\s+)?credit\s+limit\b|\bcredit\s+limit\b[^\n]{0,50}\b\d{1,3}\s*%|استخدام\s+\d{1,3}\s*%\s+من\s+(?:حدك\s+)?(?:الحد\s+الائتماني|حدك\s+الائتماني)|(?:حدك\s+الائتماني|الحد\s+الائتماني)[^\n]{0,50}\d{1,3}\s*%)/i
    return messages.flatMap(message=>{
      const timestamp=Number(message.getAttribute('date'))
      const messageType=message.getAttribute('type')
      if(!Number.isFinite(timestamp)||timestamp<cutoff||timestamp>Date.now()||messageType&&messageType!=='1')return[]
      const date=new Date(timestamp)
      const localDateTime=`${date.getFullYear()}-${String(date.getMonth()+1).padStart(2,'0')}-${String(date.getDate()).padStart(2,'0')}T${String(date.getHours()).padStart(2,'0')}:${String(date.getMinutes()).padStart(2,'0')}`
      const address=message.getAttribute('address')??''
      const body=message.getAttribute('body')??message.querySelector('body')?.textContent??''
      if(!body.trim()||verificationMessage.test(body)||creditLimitNotice.test(body)||!financialMessage.test(body))return[]
      return[`${localDateTime} | ${address} | ${body.trim()}`]
    })
  }
  return[...xml.querySelectorAll('Row,row')].map(row=>[...row.querySelectorAll('Data,data,Cell,cell')].map(cell=>(cell.textContent??'').replace(/\s+/g,' ').trim()).filter(Boolean).join(' | ')).filter(Boolean)
}
async function readSpreadsheet(file:File){
  const buffer=await file.arrayBuffer();const bytes=new Uint8Array(buffer)
  const isZip=startsWithBytes(bytes,[0x50,0x4b]);const isOle=startsWithBytes(bytes,[0xd0,0xcf,0x11,0xe0,0xa1,0xb1,0x1a,0xe1])
  if(isZip){const workbook=new Workbook();await workbook.xlsx.load(buffer);return spreadsheetLines(workbook)}
  if(isOle){const lines=await legacyBinarySpreadsheetLines(buffer);if(lines.length)return lines;throw new Error('No readable rows were found in this legacy XLS workbook.')}
  const text=decodeLegacySpreadsheet(bytes).replace(/^\uFEFF/,'').trim()
  if(!text)throw new Error('The spreadsheet is empty or could not be decoded.')
  if(/<(?:!doctype|html|table|\?xml|workbook)/i.test(text)){const lines=linesFromMarkup(text);if(lines.length)return lines}
  const lines=text.split(/\r?\n/).map(line=>line.split(/[\t;,]/).map(cell=>cell.trim()).filter(Boolean).join(' | ')).filter(Boolean)
  if(lines.length)return lines
  throw new Error('No readable rows were found in this XLS file. Save it as XLSX or CSV and try again.')
}
async function readCsv(file:File){return(await file.text()).split(/\r?\n/).map((line)=>line.split(/[,;\t]/).join(' | '))}
async function readXml(file:File){const text=await file.text();if(!/<(?:\w+:)?sms\b/i.test(text))throw new Error('This XML file does not contain Android SMS backup messages.');return linesFromMarkup(text)}
async function readPdf(file:File){const pdf=await getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise;const lines:string[]=[];for(let pageNumber=1;pageNumber<=pdf.numPages;pageNumber+=1){const page=await pdf.getPage(pageNumber);const content=await page.getTextContent();lines.push(content.items.map((item)=>'str'in item?item.str:'').join(' '))}return lines}
async function readImage(file:File,onProgress?:(progress:number)=>void){const result=await recognize(file,'eng+ara',{logger:(message)=>{if(message.status==='recognizing text'&&typeof message.progress==='number')onProgress?.(message.progress)}});return result.data.text.split(/\r?\n/)}

export async function analyzeFinancialDocument(file:File,onProgress?:(progress:number)=>void):Promise<DocumentAnalysis>{const extension=file.name.split('.').pop()?.toLowerCase();let lines:string[];if(extension==='csv')lines=await readCsv(file);else if(['xlsx','xlsm','xls'].includes(extension??''))lines=await readSpreadsheet(file);else if(extension==='xml')lines=await readXml(file);else if(extension==='pdf')lines=await readPdf(file);else if(file.type.startsWith('image/')||['png','jpg','jpeg','webp'].includes(extension??''))lines=await readImage(file,onProgress);else throw new Error('This file type is not supported.');const extractedText=lines.join('\n').trim();const operations=operationsFromLines(lines);const warnings:string[]=[];if(!extractedText)warnings.push('No recent SMS messages found in the last eight days.');if(extractedText&&!operations.length)warnings.push('Text was extracted, but no financial operations could be identified confidently.');return{operations,extractedText,warnings}}
