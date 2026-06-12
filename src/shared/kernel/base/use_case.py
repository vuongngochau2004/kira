"""Abstract base class for use cases.

Use cases represent application-level orchestration logic.
Each use case encapsulates a single business operation,
following the Command pattern for clean separation of concerns.

Example:
    >>> from src.shared.kernel.base.use_case import UseCase
    >>>
    >>> class ChatUseCase(UseCase[HandlerResult]):
    ...     def __init__(self, classifier, handler):
    ...         self.classifier = classifier
    ...         self.handler = handler
    ...
    ...     async def execute(self, query: str, user_id: str, **kwargs) -> HandlerResult:
    ...         classification = await self.classifier.classify(query, user_id)
    ...         return await self.handler.handle(query, user_id, classification)
"""

from abc import ABC, abstractmethod
from typing import TypeVar, Generic

T = TypeVar("T")


class UseCase(ABC, Generic[T]):
    """Abstract base class for all use cases.

    Use cases are the entry point for application logic in the
    modular monolith architecture. They orchestrate domain services
    and infrastructure adapters to fulfill business requirements.

    Type Parameters:
        T: The return type of the use case execution.

    All use cases MUST implement the execute() method.
    """

    @abstractmethod
    async def execute(self, *args, **kwargs) -> T:
        """Execute the use case.

        Args:
            *args: Positional arguments specific to the use case.
            **kwargs: Keyword arguments specific to the use case.

        Returns:
            The result of type T.

        Raises:
            NotImplementedError: If subclass does not implement this method.
        """
        raise NotImplementedError("Subclasses must implement execute()")
