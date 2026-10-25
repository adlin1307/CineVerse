"""
Pytest configuration and test runner fixtures for CineVerse.

Provides automatic asyncio test execution support so async tests can execute
reliably in any environment even if pytest-asyncio is not globally installed.
"""

import asyncio
import inspect
import pytest
import sys
from pathlib import Path

# Ensure backend root is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import compat  # Ensure Starlette/FastAPI compatibility across all test runs


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio event loop")


def pytest_pyfunc_call(pyfuncitem):
    """Run async test functions with asyncio if pytest-asyncio plugin is inactive."""
    testfunction = pyfuncitem.obj
    if inspect.iscoroutinefunction(testfunction):
        loop = asyncio.new_event_loop()
        try:
            asyncio.set_event_loop(loop)
            funcargs = {
                arg: pyfuncitem.funcargs[arg]
                for arg in pyfuncitem._fixtureinfo.argnames
                if arg in pyfuncitem.funcargs
            }
            loop.run_until_complete(testfunction(**funcargs))
        finally:
            loop.close()
        return True
    return None
