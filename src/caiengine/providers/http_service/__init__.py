"""Shared FastAPI utilities for CAIEngine HTTP services."""

from .app import (
    AuthDecision,
    AuthHook,
    AuthHookMiddleware,
    ErrorHandler,
    ErrorHandlingMiddleware,
    RateLimitIdentifier,
    RateLimitMiddleware,
    create_http_service_app,
)

__all__ = [
    "AuthDecision",
    "AuthHook",
    "AuthHookMiddleware",
    "ErrorHandler",
    "ErrorHandlingMiddleware",
    "RateLimitIdentifier",
    "RateLimitMiddleware",
    "create_http_service_app",
]
