import { Workbook } from 'exceljs'
import { getDocument, GlobalWorkerOptions } from 'pdfjs-dist/legacy/build/pdf.mjs'
import pdfWorker from 'pdfjs-dist/legacy/build/pdf.worker.min.mjs?url'
import { recognize } from 'tesseract.js'

GlobalWorkerOptions.workerSrc = pdfWorker

export type ExtractedOperation = { id:string; type:'Income'|'Expense'|'Transfer'|'Card payment'|'Trade'|'Deposit'|'Property'|'Unclassified'; description:string; amount:number|null; currency:string|null; date:string|null; cardLast4:string|null; confidence:number; sourceText:string }
export type DocumentAnalysis = { operations:ExtractedOperation[]; extractedText:string; warnings:string[] }

const arabicDigits:Record<string,string>={'٠':'0','١':'1','٢':'2','٣':'3','٤':'4','٥':'5','٦':'6','٧':'7','٨':'8','٩':'9','٫':'.','٬':','}
const normalizeDigits=(value:string)=>value.replace(/[٠-٩٫٬]/g,(character)=>arabicDigits[character]??character)
const amountPattern=/(?:SAR|ر\.؟س|USD|EUR|GBP|AED|JPY|\$|€|£|⃁)?\s*[-+]?\s*\d[\d,]*(?:\.\d{1,2})?/gi
const datePattern=/\b(?:\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})\b/

function classify(text:string):ExtractedOperation['type']{const value=text.toLowerCase();if(/term deposit|fixed deposit|وديعة|مرابحة/.test(value))return'Deposit';if(/property purchase|real estate purchase|شراء عقار|شراء منزل|شراء أرض/.test(value))return'Property';if(/dividend|salary|income|deposit interest|rent|توزيع|راتب|دخل|إيداع|فائدة|ايجار|إيجار/.test(value))return'Income';if(/card payment|credit card|visa|mastercard|سداد.*بطاقة|بطاقة ائتمان/.test(value))return'Card payment';if(/transfer|تحويل/.test(value))return'Transfer';if(/trade|shares?|stocks?|securit(?:y|ies)|equity|broker|شراء\s+(?:أسهم|سهم|وحدات)|بيع\s+(?:أسهم|سهم|وحدات)|تداول|أسهم|سهم/.test(value))return'Trade';if(/point of sale|\bpos\b|mada|مدى|نقاط البيع|شراء عن طريق نقاط البيع|payment|purchase|شراء|fee|withdraw|expense|فاتورة|مشتريات|رسوم|سحب|مصروف/.test(value))return'Expense';return'Unclassified'}
function currencyFrom(text:string){if(/SAR|ر\.؟س|⃁/i.test(text))return'SAR';if(/USD|\$/i.test(text))return'USD';if(/EUR|€/i.test(text))return'EUR';if(/GBP|£/i.test(text))return'GBP';if(/AED/i.test(text))return'AED';if(/JPY/i.test(text))return'JPY';return null}
function numberFromCell(value:string){const normalized=normalizeDigits(value).replace(/,/g,'').trim();if(!/^[-+]?\d+(?:\.\d{1,2})?$/.test(normalized))return null;const parsed=Number(normalized);return Number.isFinite(parsed)?parsed:null}
function statementAmountFrom(text:string,type:ExtractedOperation['type'],date:string|null){if(!date||type==='Unclassified'||!text.includes('|'))return null;const monetaryCells=text.split('|').map(cell=>numberFromCell(cell)).filter((value):value is number=>value!==null);return monetaryCells.length>=2?monetaryCells[monetaryCells.length-2]:null}
function amountFrom(text:string,cardLast4:string|null){if(/رصيد\s*(?:الإغلاق|الاغلاق)/i.test(text))return null;let value=normalizeDigits(text).replace(datePattern,' ');if(cardLast4)value=value.replace(new RegExp(`(?:[*x•]+\\s*|ending\\s+in\\s+|تنتهي\\s*(?:بـ|ب)?\\s*|رقم\\s*)?${cardLast4}\\b`,'i'),' ');const matches=[...value.matchAll(amountPattern)].map((match)=>match[0]).filter((item)=>/\d/.test(item));if(!matches.length)return null;const parsed=Number(matches[matches.length-1].replace(/[^\d.-]/g,''));return Number.isFinite(parsed)?parsed:null}
function cardLast4From(text:string){const value=normalizeDigits(text);const match=value.match(/(?:visa|mastercard|mada|card|بطاقة|مدى)[^\n]{0,45}?(?:\*+|x+|•+|ending\s+in|تنتهي\s*(?:بـ|ب)?|رقم\s*)?\s*(\d{4})\b/i);return match?.[1]??null}
function operationsFromLines(lines:string[]):ExtractedOperation[]{return lines.map((line)=>normalizeDigits(line).replace(/\s+/g,' ').trim()).filter((line)=>line.length>2).map((line,index)=>{if(/(?:رصيد\s*(?:الافتتاح|الافتتاحي|الختام|الختامي)|opening\s+balance|closing\s+balance|حساب\s+النقد)/i.test(line))return null;const cardLast4=cardLast4From(line);const type=classify(line);const date=line.match(datePattern)?.[0]??null;const amount=statementAmountFrom(line,type,date)??amountFrom(line,cardLast4);if(amount===null&&type==='Unclassified')return null;const signals=Number(amount!==null)+Number(type!=='Unclassified')+Number(date!==null)+Number(cardLast4!==null);return{id:`extracted-${index}`,type,description:line.length>110?`${line.slice(0,107)}…`:line,amount,currency:currencyFrom(line),date,cardLast4,confidence:Math.min(96,45+signals*14),sourceText:line} satisfies ExtractedOperation}).filter((item):item is ExtractedOperation=>item!==null).slice(0,100)}

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
async function readPdf(file:File){const pdf=await getDocument({data:new Uint8Array(await file.arrayBuffer())}).promise;const lines:string[]=[];for(let pageNumber=1;pageNumber<=pdf.numPages;pageNumber+=1){const page=await pdf.getPage(pageNumber);const content=await page.getTextContent();lines.push(content.items.map((item)=>'str'in item?item.str:'').join(' '))}return lines}
async function readImage(file:File,onProgress?:(progress:number)=>void){const result=await recognize(file,'eng+ara',{logger:(message)=>{if(message.status==='recognizing text'&&typeof message.progress==='number')onProgress?.(message.progress)}});return result.data.text.split(/\r?\n/)}

export async function analyzeFinancialDocument(file:File,onProgress?:(progress:number)=>void):Promise<DocumentAnalysis>{const extension=file.name.split('.').pop()?.toLowerCase();let lines:string[];if(extension==='csv')lines=await readCsv(file);else if(extension==='xlsx'||extension==='xls')lines=await readSpreadsheet(file);else if(extension==='pdf')lines=await readPdf(file);else if(file.type.startsWith('image/')||['png','jpg','jpeg','webp'].includes(extension??''))lines=await readImage(file,onProgress);else throw new Error('This file type is not supported.');const extractedText=lines.join('\n').trim();const operations=operationsFromLines(lines);const warnings:string[]=[];if(!extractedText)warnings.push('No readable text was found in this file.');if(extractedText&&!operations.length)warnings.push('Text was extracted, but no financial operations could be identified confidently.');return{operations,extractedText,warnings}}
