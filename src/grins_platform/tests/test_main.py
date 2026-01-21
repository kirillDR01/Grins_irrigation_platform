"""
Tests for main.py module.

This test suite verifies that the main module correctly exposes
the FastAPI application instance for uvicorn.
"""

import pytest
from fastapi import FastAPI

import grins_platform.main as main_module
from grins_platform.main import app


@pytest.mark.unit
class TestMainModule:
    """Test the main module exports."""

    def test_app_is_fastapi_instance(self) -> None:
        """Test that app is a FastAPI instance."""
        assert isinstance(app, FastAPI)

    def test_app_has_title(self) -> None:
        """Test that app has a title configured."""
        assert app.title is not None
        assert len(app.title) > 0

    def test_app_has_routes(self) -> None:
        """Test that app has routes registered."""
        assert len(app.routes) > 0

    def test_app_has_api_v1_routes(self) -> None:
        """Test that app has API v1 routes registered."""
        route_paths = [route.path for route in app.routes if hasattr(route, "path")]
        api_v1_routes = [path for path in route_paths if path.startswith("/api/v1")]
        assert len(api_v1_routes) > 0

    def test_app_openapi_schema(self) -> None:
        """Test that app can generate OpenAPI schema."""
        schema = app.openapi()
        assert schema is not None
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_main_module_exports_app(self) -> None:
        """Test that main module exports app in __all__."""
        assert hasattr(main_module, "__all__")
        assert "app" in main_module.__all__
