# Changelog

All notable changes to this fork of Open Interpreter will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added - From Upstream (2025-07-29)
- Remove all `pkg_resources` dependencies, replaced with `importlib.metadata`
- Update dependencies and limit Python version to `>=3.9,<3.13`
- Fix LLM temperature initialization type error (int to float)

## [0.5.0] - Fork Extensions

This fork extends the official Open Interpreter with enterprise-grade server capabilities, session management, and OpenAI-compatible APIs.

### Added

#### 🚀 Server Infrastructure
- **Initial server setup and configuration** - Complete server architecture with Flask/FastAPI
- **Process management** - PM2 ecosystem configuration for production and development
- **Supervisor integration** - Enhanced process supervision and logging
- **Deployment scripts** - Automated deployment with `server.sh` and configuration management
- **Environment configuration** - Comprehensive `.env` support and environment variable handling

#### 📦 Session Management System
- **Session persistence** - File-based session storage and retrieval
- **Session API with pagination** - RESTful API for session management with pagination support
- **Session timeout handling** - Configurable session timeout (default: longer timeout support)
- **Session lifecycle management** - Create, retrieve, update, and delete sessions
- **Inactive session cleanup** - Automatic cleanup of inactive session files
- **Workspace save/restore** - Scripts for backing up and restoring workspace data

#### 🔌 OpenAI-Compatible API
- **Full OpenAI API compatibility** - Compatible with OpenAI's Chat Completions API
- **Streaming response support** - Server-Sent Events (SSE) for real-time streaming
- **Message validation** - Robust message role and type validation
- **Content handling** - Proper string concatenation and content type handling
- **Chat completions endpoint** - `/v1/chat/completions` endpoint
- **Output limit control** - Configurable output limits for responses

#### 📊 Monitoring & Observability
- **Enhanced health check endpoint** - Detailed system information including:
  - Uptime reporting
  - LLM model information
  - Instance metadata
  - System resource status
- **Advanced logging system** - Daily log rotation with Rich console output
- **Centralized logging service** - Unified logging across all services
- **Error tracking** - Comprehensive error logging and handling

#### 🔧 API Enhancements
- **CORS support** - Configurable CORS with specific origin allowlisting
- **Preflight request handling** - Proper OPTIONS method support
- **Rate limiting** - Built-in rate limiting with configurable thresholds
- **HTTP method validation** - Method not allowed handlers for better API design
- **Error handling** - Centralized error handling and custom error responses
- **API documentation** - Comprehensive API documentation in Chinese

#### 🧪 Testing & Quality
- **Comprehensive test suite** - Full test coverage for:
  - Health check endpoints
  - Session management
  - Message operations
  - Rate limiting
  - Error scenarios
- **Test utilities** - Conditional assertions and test helpers

#### 🛠️ Developer Experience
- **Cursor rules** - Enhanced type annotations and logging rules
- **UV package manager** - UV preparation scripts for faster dependency installation
- **Poetry environment setup** - Improved Poetry configuration in deployment scripts
- **Execution permissions** - Automated `chmod_script.sh` for proper permissions
- **Production code updates** - Branch consistency and untracked file preservation

#### 🔐 Security & Authentication
- **OTP verification routes** - One-time password verification system
- **Credential management** - Secure supervisor credential handling
- **Session security** - Secure session token generation with `shortuuid`

#### 📝 Message Handling
- **ChatService integration** - Dedicated chat service layer
- **Message saving to sessions** - Automatic message persistence
- **Duplicate message prevention** - Smart duplicate detection and prevention
- **Title generation** - Automatic conversation title generation
- **Message normalization** - Consistent message format across the system
- **Default message types** - Better handling of missing message data

### Changed
- **Server script refactoring** - Improved logging and environment setup
- **App configuration** - Removed inline CORS initialization, added default settings
- **Path handling** - Updated server scripts to use base directory for logs and sockets
- **Lock optimization** - Optimized session management locks for better performance

### Fixed
- **OpenAI compatibility issues** - Removed undefined `log_error` function, added necessary imports
- **Message content handling** - Ensure message content is string before concatenation (TypeError fix)
- **JSON parsing** - Refined JSON parsing in title generation
- **Torchvision version** - More flexible version constraints (`>=0.15.0`)

### Infrastructure
- **Logging directory structure** - Reorganized log files for better management
- **Configuration centralization** - Migrated to centralized ecosystem configuration
- **Obsolete file cleanup** - Removed supervisord and deprecated configuration files

## Fork Information

**Fork Point**: December 2, 2024 (commit `21babb1`)
**Base Version**: Open Interpreter 0.4.3
**Fork Author**: ovenzeze
**Purpose**: Enterprise-grade server capabilities for Open Interpreter

### Key Differentiators

This fork focuses on:
1. **Production readiness** - Battle-tested server infrastructure
2. **API compatibility** - Drop-in replacement for OpenAI API
3. **Session management** - Persistent conversation history
4. **Monitoring** - Comprehensive observability and logging
5. **Testing** - Full test coverage for reliability

### Sync Status

- **Last upstream sync**: July 29, 2025
- **Commits ahead of upstream**: 52+
- **New features added**: 31+
- **Upstream commits integrated**: 3 (maintenance updates)

---

For the official Open Interpreter changelog, see: https://github.com/OpenInterpreter/open-interpreter/releases
