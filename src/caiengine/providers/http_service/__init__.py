"""Shared FastAPI utilities for CAIEngine HTTP services."""

from .app import (
    AuthDecision,
    AuthHook,
    AuthHookMiddleware,
    ContextIngestionRequest,
    ContextIngestionResponse,
    ContextQueryResponse,
    ContextRecord,
    ErrorHandler,
    ErrorHandlingMiddleware,
    GoalSuggestionRequest,
    GoalSuggestionResponse,
    RateLimitIdentifier,
    RateLimitMiddleware,
    TokenUsageResponse,
    create_http_service_app,
)

__all__ = [
    "AuthDecision",
    "AuthHook",
    "AuthHookMiddleware",
    "ContextIngestionRequest",
    "ContextIngestionResponse",
    "ContextQueryResponse",
    "ContextRecord",
    "ErrorHandler",
    "ErrorHandlingMiddleware",
    "GoalSuggestionRequest",
    "GoalSuggestionResponse",
    "RateLimitIdentifier",
    "RateLimitMiddleware",
    "TokenUsageResponse",
    "create_http_service_app",
]
