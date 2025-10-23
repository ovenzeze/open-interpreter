<h1 align="center">● Open Interpreter</h1>

<p align="center">
    <a href="https://discord.gg/Hvz9Axh84z">
        <img alt="Discord" src="https://img.shields.io/discord/1146610656779440188?logo=discord&style=flat&logoColor=white"/></a>
    <a href="docs/README_JA.md"><img src="https://img.shields.io/badge/ドキュメント-日本語-white.svg" alt="JA doc"/></a>
    <a href="docs/README_ZH.md"><img src="https://img.shields.io/badge/文档-中文版-white.svg" alt="ZH doc"/></a>
    <a href="docs/README_ES.md"> <img src="https://img.shields.io/badge/Español-white.svg" alt="ES doc"/></a>
    <a href="docs/README_UK.md"><img src="https://img.shields.io/badge/Українська-white.svg" alt="UK doc"/></a>
    <a href="docs/README_IN.md"><img src="https://img.shields.io/badge/Hindi-white.svg" alt="IN doc"/></a>
    <a href="LICENSE"><img src="https://img.shields.io/static/v1?label=license&message=AGPL&color=white&style=flat" alt="License"/></a>
    <br>
    <br><a href="https://0ggfznkwh4j.typeform.com/to/G21i9lJ2">Get early access to the desktop app</a>‎ ‎ |‎ ‎ <a href="https://docs.openinterpreter.com/">Documentation</a><br>
</p>

> [!IMPORTANT]
> **🚀 This is an Enhanced Fork**
>
> This repository is a production-ready fork of [Open Interpreter](https://github.com/OpenInterpreter/open-interpreter) with enterprise features:
> - **REST API Server** with OpenAI-compatible endpoints
> - **Session Management** for persistent conversations
> - **Process Management** with PM2/Supervisor support
> - **Advanced Monitoring** and structured logging
> - **Production Deployment** scripts and configuration
>
> 👉 See [FORK.md](FORK.md) for detailed fork information and [CHANGELOG.md](CHANGELOG.md) for all enhancements.
>
> 🔗 **Upstream Repository**: https://github.com/OpenInterpreter/open-interpreter

> [!NOTE]
> **Open Interpreter 1.0** is almost here.
>
> Please help test the [development branch](https://github.com/OpenInterpreter/open-interpreter/tree/development) and share your experience in the [Discord](https://discord.gg/Hvz9Axh84z):
> ```
> pip install git+https://github.com/OpenInterpreter/open-interpreter.git@development
> interpreter --help
> ```

<br>

<img alt="local_explorer" src="https://github.com/OpenInterpreter/open-interpreter/assets/63927363/d941c3b4-b5ad-4642-992c-40edf31e2e7a">

<br>
</p>
<br>

## 📚 核心文档导航

| 文档 | 描述 | 链接 |
|------|------|------|
| **分支说明** | 企业级服务器分支的详细信息和增强功能 | [FORK.md](FORK.md) |
| **贡献指南** | 如何参与项目贡献和开发流程 | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| **项目路线图** | 未来开发计划和功能规划 | [docs/ROADMAP.md](docs/ROADMAP.md) |
| **安全说明** | 安全最佳实践和注意事项 | [docs/SECURITY.md](docs/SECURITY.md) |
| **安全模式** | 实验性安全模式的使用指南 | [docs/SAFE_MODE.md](docs/SAFE_MODE.md) |
| **迁移指南** | 从其他版本迁移到此版本的详细步骤 | [docs/NCU_MIGRATION_GUIDE.md](docs/NCU_MIGRATION_GUIDE.md) |
| **变更日志** | 所有版本变更和增强功能的详细记录 | [CHANGELOG.md](CHANGELOG.md) |

## 🚀 快速开始

### 安装

```shell
pip install open-interpreter
```

> Not working? Read our [setup guide](https://docs.openinterpreter.com/getting-started/setup).

### 基本使用

```shell
interpreter
```

### Python API

```python
from interpreter import interpreter

interpreter.chat("Plot AAPL and META's normalized stock prices") # Executes a single command
interpreter.chat() # Starts an interactive chat
```

### 企业级服务器部署

```shell
# 启动 REST API 服务器
python -m interpreter.server --host 0.0.0.0 --port 8000

# 使用 PM2 进程管理
pm2 start ecosystem.config.js

# 使用 Supervisor
supervisorctl start interpreter-server
```

## 🌟 企业级特性

### REST API 服务器

此分支提供了完整的 REST API 服务器，具有 OpenAI 兼容的端点：

```python
# 示例：使用 OpenAI 兼容的 API
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"
)

response = client.chat.completions.create(
    model="gpt-4",
    messages=[{"role": "user", "content": "Hello, world!"}]
)
```

### 会话管理

- 持久化会话存储
- 会话恢复和继续
- 多用户会话隔离

### 进程管理

- PM2 配置支持
- Supervisor 集成
- 自动重启和监控

### 高级监控

- 结构化日志记录
- 性能指标收集
- 健康检查端点

## 📖 详细功能

### 终端交互

After installation, simply run `interpreter`:

```shell
interpreter
```

### GitHub Codespaces

Press the `,` key on this repository's GitHub page to create a codespace. After a moment, you'll receive a cloud virtual machine environment pre-installed with open-interpreter. You can then start interacting with it directly and freely confirm its execution of system commands without worrying about damaging the system.

## 🆚 与 ChatGPT Code Interpreter 的比较

OpenAI's release of [Code Interpreter](https://openai.com/blog/chatgpt-plugins#code-interpreter) with GPT-4 presents a fantastic opportunity to accomplish real-world tasks with ChatGPT.

However, OpenAI's service is hosted, closed-source, and heavily restricted:

- No internet access.
- [Limited set of pre-installed packages](https://wfhbrian.com/mastering-chatgpts-code-interpreter-list-of-python-packages/).
- 100 MB maximum upload, 120.0 second runtime limit.
- State is cleared (along with any generated files or links) when the environment dies.

---

Open Interpreter overcomes these limitations by running in your local environment. It has full access to the internet, isn't restricted by time or file size, and can utilize any package or library.

This combines the power of GPT-4's Code Interpreter with the flexibility of your local development environment.

## ⚙️ 高级配置

### 自定义系统消息

```python
interpreter.system_message += """
Run shell commands with -y so the user doesn't have to confirm them.
"""
print(interpreter.system_message)
```

### 更改语言模型

```shell
interpreter --model gpt-3.5-turbo
interpreter --model claude-2
interpreter --model command-nightly
```

### 本地运行

Open Interpreter 可以使用 OpenAI 兼容的服务器来运行模型。

#### 使用 LML 服务

此分支推荐使用 LML 服务，该服务运行自己的 OpenAI 兼容 API，与 OpenAI 额度无关：

```shell
interpreter --api_base "https://llm.deth.dev/v1" --api_key "your-api-key"
```

#### 使用本地模型服务器

```shell
interpreter --api_base "http://localhost:1234/v1" --api_key "fake_key"
```

#### Python 配置

```python
from interpreter import interpreter

# 使用 LML 服务
interpreter.llm.api_base = "https://llm.deth.dev/v1"
interpreter.llm.api_key = "your-api-key"

# 或使用本地服务器
# interpreter.llm.api_base = "http://localhost:1234/v1"
# interpreter.llm.api_key = "fake_key"

interpreter.chat()
```

#### 上下文窗口和最大令牌数

```shell
interpreter --local --max_tokens 1000 --context_window 3000
```

### 配置文件

```shell
interpreter --profiles
```

## 🛡️ 安全注意事项

Since generated code is executed in your local environment, it can interact with your files and system settings, potentially leading to unexpected outcomes like data loss or security risks.

**⚠️ Open Interpreter will ask for user confirmation before executing code.**

You can run `interpreter -y` or set `interpreter.auto_run = True` to bypass this confirmation, in which case:

- Be cautious when requesting commands that modify files or system settings.
- Watch Open Interpreter like a self-driving car, and be prepared to end the process by closing your terminal.
- Consider running Open Interpreter in a restricted environment like Google Colab or Replit. These environments are more isolated, reducing the risks of executing arbitrary code.

There is **experimental** support for a [safe mode](docs/SAFE_MODE.md) to help mitigate some risks.

## 🔧 工作原理

Open Interpreter equips a [function-calling language model](https://platform.openai.com/docs/guides/gpt/function-calling) with an `exec()` function, which accepts a `language` (like "Python" or "JavaScript") and `code` to run.

We then stream the model's messages, code, and your system's outputs to the terminal as Markdown.

## 📱 其他平台

### Android

The step-by-step guide for installing Open Interpreter on your Android device can be found in the [open-interpreter-termux repo](https://github.com/MikeBirdTech/open-interpreter-termux).

## 🌐 离线文档

The full [documentation](https://docs.openinterpreter.com/) is accessible on-the-go without the need for an internet connection.

[Node](https://nodejs.org/en) is a pre-requisite:

- Version 18.17.0 or any later 18.x.x version.
- Version 20.3.0 or any later 20.x.x version.
- Any version starting from 21.0.0 onwards, with no upper limit specified.

Install [Mintlify](https://mintlify.com/):

```bash
npm i -g mintlify@latest
```

Change into the docs directory and run the appropriate command:

```bash
# Assuming you're at the project's root directory
cd ./docs

# Run the documentation server
mintlify dev
```

A new browser window should open. The documentation will be available at [http://localhost:3000](http://localhost:3000) as long as the documentation server is running.

## 🤝 贡献

Thank you for your interest in contributing! We welcome involvement from the community.

Please see our [contributing guidelines](docs/CONTRIBUTING.md) for more details on how to get involved.

## 🗺️ 路线图

Visit [our roadmap](docs/ROADMAP.md) to preview the future of Open Interpreter.

## 📄 许可证

This project is licensed under the AGPL License - see the [LICENSE](LICENSE) file for details.

**Note**: This software is not affiliated with OpenAI.

![thumbnail-ncu](https://github.com/OpenInterpreter/open-interpreter/assets/63927363/1b19a5db-b486-41fd-a7a1-fe2028031686)

> Having access to a junior programmer working at the speed of your fingertips ... can make new workflows effortless and efficient, as well as open the benefits of programming to new audiences.
>
> — _OpenAI's Code Interpreter Release_

<br>