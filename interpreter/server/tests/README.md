# Open Interpreter HTTP Server Tests

This directory contains automated tests for the Open Interpreter HTTP Server API.

## Test Structure

The tests are organized in a progressive manner, from core functionality to advanced features:

- **Core Tests**: Basic health check, session management, and authentication
- **Basic Tests**: Messaging, basic chat functionality, and error handling
- **Advanced Tests**: OpenAI compatibility, streaming responses, and rate limiting

## Prerequisites

Before running the tests, make sure you have the following dependencies installed:

```bash
pip install pytest requests pytest-asyncio
```

## Running Tests

### 1. Start the Server

Make sure the Open Interpreter HTTP Server is running:

```bash
cd /path/to/open-interpreter
interpreter/server/server.sh start-dev
```

### 2. Run Tests

You can run tests at different levels depending on your needs:

#### Core Functionality Tests

```bash
cd interpreter/server
chmod +x tests/run_core_tests.sh
./tests/run_core_tests.sh
```

#### Basic Functionality Tests

```bash
cd interpreter/server
chmod +x tests/run_basic_tests.sh
./tests/run_basic_tests.sh
```

#### All Tests

```bash
cd interpreter/server
chmod +x tests/run_all_tests.sh
./tests/run_all_tests.sh
```

### 3. Individual Test Files

You can also run individual test files:

```bash
cd interpreter/server
pytest tests/core/test_health.py -v
```

## Test Configuration

The tests are configured to use:

- Server URL: `http://localhost:5002`
- API Key: `test-api-key`

If your server uses different settings, modify the fixtures in `tests/conftest.py`.

## Notes

- Tests for features that are not yet implemented will be skipped rather than failing
- Rate limiting tests may temporarily exhaust your API quota
- Some tests require specific environment variables to be set in your `.env` file 