from abc import ABC, abstractmethod


class Operation(ABC):
    """
    Base class for every WealthOS operation.
    """

    @property
    @abstractmethod
    def operation_type(self) -> str:
        """
        Unique operation identifier.
        """
        raise NotImplementedError


class OperationEngine:
    """
    Coordinates WealthOS operations.

    It does not contain business logic.
    It only delegates execution to the appropriate strategy.
    """

    def execute(self, operation: Operation):
        raise NotImplementedError