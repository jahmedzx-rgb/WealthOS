import type { Loan } from '../services/accountingService'

function dueDate(year:number,month:number,day:number){
  const last=new Date(year,month+1,0).getDate()
  return new Date(year,month,Math.min(day,last),12)
}

export function projectedEarlySettlement(loan:Loan, today=new Date()){
  const saved=Number(loan.private_details?.early_settlement_amount)
  const asOfValue=loan.private_details?.opening_balance_date
  if(!Number.isFinite(saved)||saved<=0||!asOfValue)return null
  const asOf=new Date(`${asOfValue}T12:00:00`)
  if(Number.isNaN(asOf.getTime()))return null
  const paymentDay=Number(loan.private_details?.payment_day??loan.first_payment_date?.slice(-2)??1)
  let next=dueDate(asOf.getFullYear(),asOf.getMonth(),paymentDay)
  if(next<=asOf)next=dueDate(asOf.getFullYear(),asOf.getMonth()+1,paymentDay)
  let amount=saved
  let installments=0
  const monthlyRate=Number(loan.annual_rate||0)/1200
  const payment=Number(loan.monthly_payment||0)
  const maximum=Number(loan.private_details?.remaining_installments??600)
  while(next<=today&&installments<maximum&&amount>0){
    const profit=amount*monthlyRate
    amount=Math.max(0,amount-Math.max(0,payment-profit))
    installments+=1
    next=dueDate(next.getFullYear(),next.getMonth()+1,paymentDay)
  }
  return {amount:Number(amount.toFixed(2)),installments,asOf:asOfValue}
}
