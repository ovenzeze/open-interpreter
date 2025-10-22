# Open Interpreter - Enterprise Server Fork

This is an enhanced fork of [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) with production-grade server capabilities, session management, and OpenAI-compatible APIs.

## 🎯 Why This Fork?

The official Open Interpreter is designed primarily as a terminal interface and Python library. This fork extends it to be a **production-ready server application** suitable for:

- **Multi-user environments** - Session-based architecture for concurrent users
- **API integrations** - OpenAI-compatible REST API endpoints
- **Production deployments** - Complete process management and monitoring
- **Enterprise features** - Logging, error handling, rate limiting, and observability

## 🚀 Key Features

### 1. Server Infrastructure

Complete server setup with multiple deployment options:

```bash
# Development mode
./server.sh dev

# Production mode with PM2
./server.sh prod

# Production mode with Supervisor
./server.sh supervisor
```

**Features:**
- Flask/FastAPI-based REST API
- PM2 ecosystem configuration
- Supervisor integration
- Auto-restart and crash recovery
- Environment-based configuration

### 2. Session Management

Persistent conversation sessions with full lifecycle management:

```bash
# List all sessions
GET /api/sessions?page=1&limit=10

# Create new session
POST /api/sessions

# Get session by ID
GET /api/sessions/{session_id}

# Delete session
DELETE /api/sessions/{session_id}
```

**Features:**
- File-based persistence
- Pagination support
- Automatic cleanup
- Workspace backup/restore
- Session timeout handling

### 3. OpenAI-Compatible API

Drop-in replacement for OpenAI's Chat Completions API:

```bash
POST /v1/chat/completions
Content-Type: application/json

{
  "model": "gpt-4",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ],
  "stream": true
}
```

**Features:**
- Full OpenAI API compatibility
- Streaming via Server-Sent Events
- Message validation
- Output limit control
- Error handling

### 4. Monitoring & Observability

Comprehensive monitoring endpoints:

```bash
# Health check with system info
GET /health

# Response includes:
{
  "status": "healthy",
  "uptime": "2h 30m 15s",
  "llm_model": "gpt-4",
  "instance_id": "...",
  "version": "0.5.0"
}
```

**Features:**
- Real-time health checks
- Uptime reporting
- Resource monitoring
- Structured logging with rotation
- Rich console output

### 5. Security & CORS

Production-ready security features:

- Configurable CORS policies
- Origin whitelisting
- Rate limiting
- OTP verification (optional)
- Secure credential management

## 📊 Comparison with Upstream

| Feature | Upstream | This Fork |
|---------|----------|-----------|
| Terminal Interface | ✅ | ✅ |
| Python Library | ✅ | ✅ |
| REST API Server | ❌ | ✅ |
| Session Management | ❌ | ✅ |
| OpenAI API Compatible | ❌ | ✅ |
| Process Management | ❌ | ✅ |
| Production Logging | Basic | Advanced |
| Multi-user Support | ❌ | ✅ |
| Health Monitoring | ❌ | ✅ |
| Test Coverage | Partial | Comprehensive |

## 🔧 Installation

Same as upstream, with additional server dependencies:

```bash
# Install base package
pip install -e .

# Install with server extras
pip install -e ".[server]"

# Or using poetry
poetry install --extras server
```

## 🏃 Quick Start

### As a Server

```bash
# Start the server
./server.sh dev

# Test the API
curl http://localhost:8000/health

# Use OpenAI-compatible endpoint
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": true
  }'
```

### As Original CLI

All original functionality is preserved:

```bash
# Terminal interface (unchanged)
interpreter

# Python usage (unchanged)
from interpreter import interpreter
interpreter.chat("Plot AAPL stock price")
```

## 📚 Documentation

- **API Documentation**: See `docs/API.md` (Chinese)
- **Changelog**: See `CHANGELOG.md`
- **Original Docs**: https://docs.openinterpreter.com/

## 🔄 Sync Status

- **Fork Point**: December 2, 2024 (commit `21babb1`)
- **Base Version**: 0.4.3
- **Last Sync**: July 29, 2025
- **Commits Ahead**: 52+
- **New Features**: 31+

### Upstream Changes Integrated

✅ Remove `pkg_resources`, use `importlib.metadata`
✅ Update dependencies, limit Python version
✅ Fix LLM temperature type error

## 🤝 Contributing

This fork accepts contributions focused on:

1. **Server features** - Session management, APIs, deployment
2. **Enterprise capabilities** - Monitoring, logging, security
3. **Bug fixes** - For fork-specific features
4. **Upstream sync** - Help keep in sync with official releases

For contributing to the core Open Interpreter features, please submit to the [upstream repository](https://github.com/OpenInterpreter/open-interpreter).

## 📜 License

Same as upstream: AGPL-3.0

## 🙏 Acknowledgments

This project is built on top of [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) by Killian Lucas and contributors.

**Upstream Repository**: https://github.com/OpenInterpreter/open-interpreter
**Fork Maintainer**: [@ovenzeze](https://github.com/ovenzeze)

## 🔗 Links

- **Official Open Interpreter**: https://github.com/OpenInterpreter/open-interpreter
- **Official Docs**: https://docs.openinterpreter.com/
- **Official Discord**: https://discord.gg/Hvz9Axh84z

---

**Note**: This is an independent fork maintained separately from the official Open Interpreter project. While we strive to stay in sync with upstream, this fork contains significant additional features focused on server deployment and enterprise use cases.
