import { useEffect, useRef, useState, type ChangeEvent, type DragEvent } from 'react'
import { ArrowDown, ArrowRight, ArrowUp, Check, ChevronLeft, ChevronRight, EyeOff, FileSearch, Send, Settings2, ShieldCheck, Sparkles, TriangleAlert, Upload, X, Zap } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { operationEngine } from '../../operations/operationEngine'
import { analyzeFinancialDocument, type DocumentAnalysis, type ExtractedOperation } from '../../services/documentImportService'
import { getPendingImportBatches, saveImportBatch, updateImportedOperation } from '../../services/importReviewService'
import Card from '../ui/Card'
import './Operations.css'
import './OperationsImportAnalysis.css'
import './OperationsImportPagination.css'
import './OperationsImportViewport.css'
import './OperationsCardMatching.css'
import './OperationsReviewCompletion.css'
import { useLanguage } from '../../context/LanguageContext'
import { getAccountPreferences, updateAccountPreferences } from '../../services/accountService'
import { formatDisplayInteger, formatDisplayNumber, formatDisplayPercent } from '../../utils/localeFormat'

function getNineQuickActionIds(preferred: string[] = []) {
  const availableIds = operationEngine.getAll().filter((item)=>item.status==='active').map((item) => item.id)
  return [...new Set([...preferred, ...operationEngine.getQuickActions().map((item) => item.id), ...availableIds])]
    .filter((id) => availableIds.includes(id))
    .slice(0, 9)
}

export default function Operations() {
  const {language,t,direction}=useLanguage()
  const navigate = useNavigate()
  const fileInput = useRef<HTMLInputElement>(null)
  const [command, setCommand] = useState('')
  const [commandOpen, setCommandOpen] = useState(false)
  const [quickActionIds,setQuickActionIds]=useState(()=>getNineQuickActionIds())
  const [customizeOpen,setCustomizeOpen]=useState(false)
  const [savingPreferences,setSavingPreferences]=useState(false)
  const [dragging, setDragging] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [analysis, setAnalysis] = useState<DocumentAnalysis | null>(null)
  const [analysisError, setAnalysisError] = useState('')
  const [analysisProgress, setAnalysisProgress] = useState(0)
  const [analyzing, setAnalyzing] = useState(false)
  const [currentPage, setCurrentPage] = useState(1)
  const [ignoredIds, setIgnoredIds] = useState<string[]>([])
  const [confirmedIds, setConfirmedIds] = useState<string[]>([])
  const [savingReview, setSavingReview] = useState(false)
  const [saveError, setSaveError] = useState('')
  const [pendingReviewCount, setPendingReviewCount] = useState(0)
  const [savedOperationIds, setSavedOperationIds] = useState<Record<string, number>>({})
  const [archiveReady, setArchiveReady] = useState(false)

  useEffect(()=>{getPendingImportBatches().then((batches)=>setPendingReviewCount(batches.reduce((total,batch)=>total+batch.operations.filter((item)=>item.status==='PENDING').length,0))).catch(()=>undefined)},[])
  useEffect(()=>{getAccountPreferences().then((value)=>setQuickActionIds(getNineQuickActionIds(value.quick_action_ids??[]))).catch(()=>undefined)},[])

  const quickActions=quickActionIds.map((id)=>operationEngine.get(id)).filter((item): item is NonNullable<typeof item>=>item!==null)
  const customizableActions=[...quickActions,...operationEngine.getAll().filter((action)=>action.status==='active'&&!quickActionIds.includes(action.id)).sort((a,b)=>a.order-b.order)]
  const toggleQuickAction=(id:string)=>setQuickActionIds((current)=>current.includes(id)?current:getNineQuickActionIds([...current.slice(0,8),id]))
  const moveQuickAction=(id:string,direction:-1|1)=>setQuickActionIds((current)=>{const index=current.indexOf(id);const target=index+direction;if(index<0||target<0||target>=current.length)return current;const next=[...current];[next[index],next[target]]=[next[target],next[index]];return next})
  const saveQuickActions=async()=>{setSavingPreferences(true);try{await updateAccountPreferences(quickActionIds);setCustomizeOpen(false)}finally{setSavingPreferences(false)}}

  async function openReview(file?: File) {
    if (!file) return
    setSelectedFile(file); setAnalysis(null); setAnalysisError(''); setSaveError(''); setAnalysisProgress(0); setAnalyzing(true); setSavingReview(false); setCurrentPage(1); setIgnoredIds([]); setConfirmedIds([]); setSavedOperationIds({}); setArchiveReady(false)
    try {
      const result = await analyzeFinancialDocument(file, setAnalysisProgress)
      setAnalysis(result)
      setSavingReview(true)
      const saved = await saveImportBatch(file, result.operations, [], [])
      setSavedOperationIds(Object.fromEntries(result.operations.map((item, index) => [item.id, saved.operations[index]?.id]).filter((entry): entry is [string, number] => typeof entry[1] === 'number')))
      setArchiveReady(true)
      setPendingReviewCount((count)=>count+result.operations.length)
    }
    catch (error) { setAnalysisError(error instanceof Error ? error.message : 'The document could not be analyzed.') }
    finally { setAnalyzing(false); setSavingReview(false) }
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) { void openReview(event.target.files?.[0]); event.target.value = '' }
  function handleDrop(event: DragEvent<HTMLDivElement>) { event.preventDefault(); setDragging(false); void openReview(event.dataTransfer.files?.[0]) }

  const pageSize = 6
  const visibleOperations = analysis?.operations.filter((item) => !ignoredIds.includes(item.id) && !confirmedIds.includes(item.id)) ?? []
  const totalPages = Math.max(1, Math.ceil(visibleOperations.length / pageSize))
  const pagedOperations = visibleOperations.slice((currentPage - 1) * pageSize, currentPage * pageSize)
  async function decideOperation(id:string,status:'IGNORED'){
    const savedId=savedOperationIds[id]
    if(!savedId){setSaveError('This operation has not been archived yet. Please wait and try again.');return}
    setSaveError('')
    try{
      await updateImportedOperation(savedId,status)
      const nextPages=Math.max(1,Math.ceil((visibleOperations.length-1)/pageSize))
      setIgnoredIds((ids)=>[...ids,id])
      setPendingReviewCount((count)=>Math.max(0,count-1));setCurrentPage((page)=>Math.min(page,nextPages))
    }catch(error){setSaveError(error instanceof Error?error.message:'The decision could not be saved.')}
  }
  function ignoreOperation(id:string){void decideOperation(id,'IGNORED')}
  function reviewOperation(item:ExtractedOperation){const savedId=savedOperationIds[item.id];if(!savedId){setSaveError('This operation has not been archived yet. Please wait and try again.');return}const route=item.type==='Income'?'/operations/income':item.type==='Transfer'?'/operations/transfer':item.type==='Card payment'?'/operations/card-payment':item.type==='Trade'?'/operations/trade':item.type==='Expense'?'/operations/expense':item.type==='Deposit'?'/operations/deposit':item.type==='Property'?'/operations/property':'/operations';navigate(route,{state:{importedOperation:{id:savedId,operation_type:item.type,description:item.description,amount:item.amount,currency:item.currency,transaction_date:item.date,card_last4:item.cardLast4,confidence:item.confidence,source_text:item.sourceText,status:'PENDING',matched_entity_type:null,matched_entity_id:null,posting_reference:null,posted_at:null}}})}
  const knownCards:Record<string,string>={'9214':'SAB Visa Infinite','1842':'Mastercard World','6031':'Travel Card'}
  const cardsToDefine = [...new Set((analysis?.operations ?? []).filter((item)=>confirmedIds.includes(item.id)&&item.cardLast4&&!knownCards[item.cardLast4]).map((item)=>item.cardLast4 as string))]
  async function reviewLater(){if(!selectedFile||!analysis)return;if(!archiveReady){setSaveError('Please wait while WealthOS adds this document to your library.');return}setSelectedFile(null)}

  return <Card icon={Zap} title="Quick Actions" action={<div className="operations__header-actions"><button className="operations__customize" type="button" aria-label="Customize Quick Actions" title="Customize Quick Actions" onClick={()=>setCustomizeOpen(true)}><Settings2 size={15}/></button><button className="operations__view-all" type="button" onClick={() => navigate('/operations')}>{t('View all')}<ArrowRight size={16} style={direction==='rtl'?{transform:'rotate(180deg)'}:undefined}/></button></div>}>
    <div className="operations">{quickActions.map((action) => { if(!action)return null;const Icon=action.icon; return <button key={action.id} className="operations__card" type="button" onClick={() => navigate(action.route)}><div className="operations__icon"><Icon size={18}/></div><span>{t(action.title)}</span></button> })}</div>

    {customizeOpen&&<div className="operations__customize-modal" role="dialog" aria-modal="true" aria-labelledby="customize-actions-title" onMouseDown={(event)=>{if(event.currentTarget===event.target)setCustomizeOpen(false)}}><section><header><div><small>Personal Workspace</small><h3 id="customize-actions-title">Customize Quick Actions</h3><p>All {customizableActions.length} operations are available. Keep 9 visible and ordered by priority.</p></div><button type="button" aria-label="Close" onClick={()=>setCustomizeOpen(false)}><X size={17}/></button></header><div className="operations__customize-list">{customizableActions.map((action)=>{const Icon=action.icon;const selected=quickActionIds.includes(action.id);const index=quickActionIds.indexOf(action.id);return <article className={selected?'is-selected':''} key={action.id}><button className="operations__customize-toggle" type="button" onClick={()=>toggleQuickAction(action.id)}><span><Icon size={16}/></span><div><strong>{action.title}</strong><small>{action.description} · {action.status}</small></div><i>{selected?'Shown':'Replace Last'}</i></button>{selected&&<nav><button type="button" aria-label={`Move ${action.title} up`} disabled={index===0} onClick={()=>moveQuickAction(action.id,-1)}><ArrowUp size={13}/></button><button type="button" aria-label={`Move ${action.title} down`} disabled={index===quickActionIds.length-1} onClick={()=>moveQuickAction(action.id,1)}><ArrowDown size={13}/></button></nav>}</article>})}</div><footer><span>{customizableActions.length} Available · 9 Shown · Ordered by priority</span><button type="button" disabled={savingPreferences||quickActionIds.length!==9} onClick={()=>void saveQuickActions()}>{savingPreferences?'Saving…':'Save Layout'}</button></footer></section></div>}

    <section className="operations__import">
      <input ref={fileInput} className="operations__file-input" type="file" accept=".pdf,.png,.jpg,.jpeg,.webp,.xlsx,.xls,.csv" onChange={handleFileChange}/>
      <div className={`operations__dropzone${dragging?' is-dragging':''}`} role="button" tabIndex={0} onClick={() => fileInput.current?.click()} onKeyDown={(event) => { if(event.key==='Enter'||event.key===' ')fileInput.current?.click() }} onDragEnter={(event) => { event.preventDefault(); setDragging(true) }} onDragOver={(event) => event.preventDefault()} onDragLeave={() => setDragging(false)} onDrop={handleDrop}>
        <span className="operations__dropzone-icon"><Upload size={18}/></span><div><strong>{t('Import financial document')}</strong><small>{t('PDF, image, XLSX or CSV')}</small></div><span className="operations__browse">{t('Browse')}</span>
      </div>
      <div className="operations__tools-row">{pendingReviewCount>0?<Link className="operations__pending" to="/accounting/review-queue"><span><i/>{formatDisplayInteger(pendingReviewCount,language)} {t('operations awaiting review')}</span><ArrowRight size={13}/></Link>:<span className="operations__pending operations__pending--empty"><span>{t('No pending reviews')}</span></span>}<button className="operations__command-trigger" type="button" onClick={()=>setCommandOpen(true)}><FileSearch size={13}/> {t('Or describe a transaction')}</button></div>
      {commandOpen&&<div className="operations__command-modal" role="dialog" aria-modal="true" aria-labelledby="quick-command-title" onMouseDown={(event)=>{if(event.currentTarget===event.target)setCommandOpen(false)}}>
        <section><header><div><small>Quick Operation</small><h3 id="quick-command-title">Describe A Transaction</h3></div><button type="button" aria-label="Close" onClick={()=>setCommandOpen(false)}><X size={17}/></button></header>
          <p>Tell WealthOS what you want to record, and we will take you to the matching operation.</p>
          <form onSubmit={(event)=>{event.preventDefault();if(command.trim()){setCommandOpen(false);navigate('/operations',{state:{command:command.trim()}})}}}>
            <Sparkles size={16}/><input autoFocus aria-label="Quick operation command" placeholder="Transfer SAR 5,000 from SAB to Al Rajhi" value={command} onChange={(event)=>setCommand(event.target.value)}/><button disabled={!command.trim()} type="submit"><Send size={15}/> Continue</button>
          </form>
        </section>
      </div>}
    </section>

    {selectedFile && <div className="import-modal" role="dialog" aria-modal="true" aria-labelledby="import-review-title" onMouseDown={(event) => { if(event.currentTarget===event.target)setSelectedFile(null) }}><section className="import-modal__panel">
      <header><div><p>{t('Document intelligence')}</p><h2 id="import-review-title">{t('Review imported operations')}</h2><span>{selectedFile.name} · {formatDisplayInteger(Math.max(selectedFile.size/1024,1),language)} KB</span></div><button type="button" aria-label={t('Close import review')} onClick={() => setSelectedFile(null)}><X size={18}/></button></header>
      <div className="import-modal__guard"><ShieldCheck size={17}/><span><strong>{t('Local, review-first analysis.')}</strong> {t('The file is read in your browser and nothing is posted automatically.')}</span></div>
      {analyzing ? <div className="import-modal__loading"><Sparkles size={18}/><strong>{t('Reading the actual file…')}</strong><span>{analysisProgress>0?`${formatDisplayPercent(analysisProgress*100,0,language)} ${t('OCR progress')}`:t('Extracting rows and financial data')}</span></div> : analysisError ? <div className="import-modal__error"><TriangleAlert size={17}/><span><strong>{t('Analysis failed')}</strong>{t(analysisError)}</span></div> : analysis && <div className="import-modal__summary"><div><strong>{formatDisplayInteger(visibleOperations.length,language)}</strong><span>{t('Awaiting decision')}</span></div><div><strong>{formatDisplayInteger(confirmedIds.length,language)}</strong><span>{t('Confirmed')}</span></div><div><strong>{formatDisplayInteger(ignoredIds.length,language)}</strong><span>{t('Ignored')}</span></div></div>}
      <div className="import-modal__list">
        {analysis?.warnings.map((warning) => <div className="import-modal__warning" key={warning}><TriangleAlert size={15}/>{t(warning)}</div>)}
        {pagedOperations.map((item) => { const knownCard=item.cardLast4?knownCards[item.cardLast4]:null; return <article key={item.id}><i className={item.confidence<80?'needs-review':''}>{item.confidence<80?<TriangleAlert size={15}/>:<Check size={15}/>}</i><div><strong>{t(item.type)}</strong><small>{item.description}</small>{item.date&&<small>{item.date}</small>}{item.cardLast4&&<span className={`import-modal__card-match${knownCard?'':' is-unknown'}`}>{knownCard?`${knownCard} •• ${item.cardLast4}`:`${t('Unrecognized card')} •• ${item.cardLast4} · ${t('Define during review')}`}</span>}</div><div><strong>{item.amount===null?t('Amount not found'):`${item.currency??''} ${formatDisplayNumber(item.amount,undefined,language)}`.trim()}</strong><small>{formatDisplayPercent(item.confidence,0,language)} {t('confidence')}</small></div><div className="import-modal__row-actions"><button className="is-ignore" type="button" onClick={()=>ignoreOperation(item.id)}><EyeOff size={13}/>{t('Ignore')}</button><button type="button" onClick={()=>reviewOperation(item)}><ArrowRight size={14} style={direction==='rtl'?{transform:'rotate(180deg)'}:undefined}/>{t('Review & Post')}</button></div></article> })}
      </div>
      {!visibleOperations.length&&analysis&&<div className="import-modal__complete"><Check size={18}/><div><strong>{t('All operations have a decision')}</strong><span>{cardsToDefine.length?`${formatDisplayInteger(cardsToDefine.length,language)} ${t(cardsToDefine.length>1?'unrecognized cards can now be defined without interrupting the review.':'unrecognized card can now be defined without interrupting the review.')}`:t('No new cards need to be defined.')}</span></div></div>}
      {saveError&&<div className="import-modal__error"><TriangleAlert size={15}/><span><strong>{t('Could not save review')}</strong>{t(saveError)}</span></div>}
      <footer><span>{visibleOperations.length?`${t('Showing')} ${formatDisplayInteger(Math.min((currentPage-1)*pageSize+1,visibleOperations.length),language)}–${formatDisplayInteger(Math.min(currentPage*pageSize,visibleOperations.length),language)} ${t('of')} ${formatDisplayInteger(visibleOperations.length,language)}`:`${formatDisplayInteger(confirmedIds.length,language)} ${t('confirmed')} · ${formatDisplayInteger(ignoredIds.length,language)} ${t('ignored')}`}</span>{visibleOperations.length?<nav className="import-modal__pagination" aria-label={t('Imported operations pages')}><button type="button" disabled={currentPage===1} onClick={()=>setCurrentPage((page)=>page-1)} aria-label={t('Previous page')}><ChevronLeft size={14}/></button><strong>{t('Page')} {formatDisplayInteger(currentPage,language)} {t('of')} {formatDisplayInteger(totalPages,language)}</strong><button type="button" disabled={currentPage===totalPages} onClick={()=>setCurrentPage((page)=>page+1)} aria-label={t('Next page')}><ChevronRight size={14}/></button></nav>:cardsToDefine.length?<button className="import-modal__continue" type="button" onClick={()=>navigate('/operations/credit-card-account',{state:{last4:cardsToDefine[0]}})}>{t('Continue to card setup')} <ArrowRight size={14} style={direction==='rtl'?{transform:'rotate(180deg)'}:undefined}/></button>:null}<button type="button" disabled={savingReview||!analysis||!archiveReady} onClick={()=>void reviewLater()}>{t(savingReview?'Adding To Library…':'Review Later')}</button></footer>
    </section></div>}
  </Card>
}
