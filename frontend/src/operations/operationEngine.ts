import {
  operationRegistry,
  type OperationDefinition,
} from './operationRegistry'

export class OperationEngine {
  get(
    operationId: string,
  ): OperationDefinition | null {
    return (
      operationRegistry[operationId] ?? null
    )
  }

  getAll(): OperationDefinition[] {
    return Object.values(
      operationRegistry,
    )
  }

  getActive(): OperationDefinition[] {
    return this.getAll().filter(
      (operation) =>
        operation.status === 'active',
    )
  }

  getQuickActions(): OperationDefinition[] {
    return this.getAll()
      .filter(
        (operation) =>
          operation.quickAction,
      )
      .sort(
        (a, b) => a.order - b.order,
      )
      .slice(0, 9)
  }

  getByCategory(
    category: OperationDefinition['category'],
  ): OperationDefinition[] {
    return this.getActive()
      .filter(
        (operation) =>
          operation.category === category,
      )
      .sort(
        (a, b) => a.order - b.order,
      )
  }

  exists(operationId: string): boolean {
    return operationId in operationRegistry
  }
}

export const operationEngine =
  new OperationEngine()
