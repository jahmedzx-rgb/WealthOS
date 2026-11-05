export type CardReminderStage = 'issued' | 'fifteen' | 'five' | 'due' | 'overdue'

export function cardReminderStage(daysUntil: number | null, statementIssued: boolean, issuedBalance: number): CardReminderStage | null {
  if (!statementIssued || issuedBalance <= 0 || daysUntil === null) return null
  if (daysUntil < 0) return 'overdue'
  if (daysUntil === 0) return 'due'
  if (daysUntil <= 5) return 'five'
  if (daysUntil <= 15) return 'fifteen'
  return 'issued'
}
