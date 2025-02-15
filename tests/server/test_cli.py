"""
Tests for Open Interpreter HTTP Server CLI
"""

from unittest.mock import patch

import pytest
from click.testing import CliRunner

from interpreter.server.cli import main


@pytest.fixture
def runner():
    """Create CLI test runner"""
    return CliRunner()


def test_cli_default_options(runner):
    """Test CLI with default options"""
    with patch('interpreter.server.cli.create_app') as mock_create_app, \
         patch('interpreter.server.cli.serve') as mock_serve:
        
        result = runner.invoke(main)
        assert result.exit_code == 0
        
        # Check if app was created
        mock_create_app.assert_called_once()
        
        # Check if server was started with default options
        mock_serve.assert_called_once()
        args, kwargs = mock_serve.call_args
        assert kwargs['host'] == '0.0.0.0'
        assert kwargs['port'] == 5001


def test_cli_custom_options(runner):
    """Test CLI with custom options"""
    with patch('interpreter.server.cli.create_app') as mock_create_app, \
         patch('interpreter.server.cli.serve') as mock_serve:
        
        result = runner.invoke(main, ['--host', 'localhost', '--port', '8080'])
        assert result.exit_code == 0
        
        # Check if app was created
        mock_create_app.assert_called_once()
        
        # Check if server was started with custom options
        mock_serve.assert_called_once()
        args, kwargs = mock_serve.call_args
        assert kwargs['host'] == 'localhost'
        assert kwargs['port'] == 8080


def test_cli_debug_mode(runner):
    """Test CLI in debug mode"""
    with patch('interpreter.server.cli.create_app') as mock_create_app, \
         patch.object(mock_create_app.return_value, 'run') as mock_run:
        
        result = runner.invoke(main, ['--debug'])
        assert result.exit_code == 0
        
        # Check if app was created
        mock_create_app.assert_called_once()
        
        # Check if Flask debug server was started
        mock_run.assert_called_once_with(host='0.0.0.0', port=5001, debug=True) 