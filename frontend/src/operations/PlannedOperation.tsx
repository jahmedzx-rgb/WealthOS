import OperationForm from './OperationForm'

type Kind = 'expense' | 'card-payment' | 'buy-asset' | 'sell-asset' | 'journal-entry' | 'bank-account' | 'credit-card-account' | 'bank-card' | 'property' | 'property-valuation'
const definitions: Record<Kind, { title: string; fields: string[] }> = {
  expense: { title: 'تفاصيل المصروف', fields: ['فئة المصروف', 'حساب السداد', 'المبلغ', 'تاريخ المعاملة', 'الوصف'] },
  'card-payment': { title: 'سداد بطاقة ائتمانية', fields: ['البطاقة الائتمانية', 'حساب السداد', 'المبلغ', 'تاريخ السداد', 'المرجع'] },
  'buy-asset': { title: 'شراء أصل', fields: ['نوع الأصل', 'اسم الأصل', 'حساب السداد', 'مبلغ الشراء', 'تاريخ الشراء'] },
  'sell-asset': { title: 'بيع أصل', fields: ['الأصل', 'حساب الوجهة', 'مبلغ البيع', 'تاريخ البيع', 'الرسوم'] },
  'journal-entry': { title: 'قيد يدوي', fields: ['الوصف', 'الحساب المدين', 'الحساب الدائن', 'المبلغ', 'تاريخ الترحيل'] },
  'bank-account': { title: 'تفاصيل الحساب البنكي', fields: ['البنك', 'نوع الحساب', 'اسم الحساب', 'رقم الآيبان أو الحساب', 'العملة'] },
  'credit-card-account': { title: 'تفاصيل البطاقة الائتمانية', fields: ['البنك المصدر', 'اسم البطاقة', 'آخر 4 أرقام', 'الحد الائتماني', 'العملة'] },
  'bank-card': { title: 'تفاصيل بطاقة الخصم', fields: ['الحساب البنكي المرتبط', 'اسم البطاقة', 'آخر 4 أرقام', 'شبكة البطاقة', 'العملة'] },
  property: { title: 'تفاصيل العقار', fields: ['نوع العقار', 'اسم العقار', 'نسبة الملكية', 'قيمة الشراء', 'تاريخ الشراء'] },
  'property-valuation': { title: 'تقييم العقار', fields: ['العقار', 'مصدر التقييم', 'القيمة السوقية', 'تاريخ التقييم', 'ملاحظات'] },
}

export default function PlannedOperation({ type }: { type: Kind }) {
  const item = definitions[type]
  return <OperationForm title={item.title} onSubmit={(event) => event.preventDefault()}>
    <div className="standard-operation__grid">
      {item.fields.map((field, index) => <label key={field}><span>{field}</span>{index < 2
        ? <select defaultValue=""><option value="" disabled>اختر {field}</option></select>
        : <input type={/تاريخ/.test(field) ? 'datetime-local' : /مبلغ|رسوم|قيمة/.test(field) ? 'number' : 'text'} placeholder={field} />}</label>)}
    </div>
    <div className="income-operation__actions"><span>هذه العملية مخططة ولا تحفظ البيانات حاليًا.</span><button type="submit" disabled>قريبًا</button></div>
  </OperationForm>
}
