"""
Pytest configuration for server tests
"""

import os
import sys
import pytest
from interpreter.server import create_app

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

@pytest.fixture
def app():
    """Create application for the tests."""
    app = create_app({
        'TESTING': True,
        'LOG_LEVEL': 'DEBUG',
        'MAX_ACTIVE_INSTANCES': 3,
        'INSTANCE_TIMEOUT': 300,
        'CLEANUP_INTERVAL': 60
    })
    return app

@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """Create a test runner for the app's Click commands."""
    return app.test_cli_runner()