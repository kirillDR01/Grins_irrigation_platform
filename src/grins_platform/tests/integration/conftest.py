"""Integration test conftest - imports fixtures for integration tests.

This conftest imports all fixtures from fixtures.py to make them
available to integration tests.
"""

# Import all fixtures from fixtures.py using wildcard import
# This makes all fixtures available to integration tests
from grins_platform.tests.integration.fixtures import *  # noqa: F403
