"""
Main entry point for the Grin's Irrigation Platform API.

This module exposes the FastAPI application instance for uvicorn.

Usage:
    uvicorn grins_platform.main:app --reload
"""

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from grins_platform.app import app  # noqa: E402

__all__ = ["app"]
