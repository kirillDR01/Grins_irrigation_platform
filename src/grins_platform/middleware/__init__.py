"""
Middleware package for the Grins Platform.

This package contains middleware components for request/response processing.
"""

from grins_platform.middleware.csrf import CSRFMiddleware

__all__ = ["CSRFMiddleware"]
