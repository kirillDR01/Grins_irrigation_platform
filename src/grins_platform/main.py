"""
Main entry point for the Grin's Irrigation Platform API.

This module exposes the FastAPI application instance for uvicorn.

Usage:
    uvicorn grins_platform.main:app --reload
"""

from grins_platform.app import app

__all__ = ["app"]
