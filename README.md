# GitIQ

GitIQ is an AI pair programming tool that uses Git as the interface rather than embedding in an IDE.

## Quick Start

To run the application:

```
OPENAI_API_KEY=xxxx python agent/app.py
```

## Configuration

GitIQ uses a `config.json` file for various settings:

### Git Configuration

```json
"git": {
  "name": "GitIQ Bot",
  "email": "gitiq-bot@gmail.com"
}
```

This sets the Git user name and email for commits made by GitIQ.

### LLM API Configuration

```json
"llm_apis": {
  "openai": { "api_base": "https://api.openai.com/v1", "api_key": "OPENAI_API_KEY" },
  "lmproxy": { "api_base": "https://api.lmproxy.org/v1", "api_key": "OPENAI_API_KEY" }
}
```

This section defines the LLM API endpoints and their corresponding API keys. API keys are specified as environment variable names.

### Model Configuration

```json
"models": {
  "Claude 3.5 Sonnet": { "llm_api": "claude", "name": "claude-3-5-sonnet-20240620", "nojson": true },
  "OpenAI o1-preview (via OpenRouter)": { "llm_api": "openrouter", "name": "openai/o1-preview" }
}
```

This section defines the available models, specifying which API to use, the model name, and any special flags like `nojson` for models that don't support JSON output.

## Documentation

- [Product Requirements Document](PRD.md)
- [API Specification](API.md)
- [Style Guide](Style_Guide.md)

## Overview

GitIQ allows developers to describe changes in natural language and receive complete Pull Requests. It uses Git commits to maintain a clear history of AI-human collaboration.

## Key Features

- Uses Git as the primary interface
- Preserves context and decision-making through commit messages
- Handles multi-file changes as coherent units of work
- Creates reviewable PRs
- Works with any editor/IDE since changes flow through Git
- Supports multiple LLM providers and models through flexible configuration

## Contributing

Please read our [Style Guide](Style_Guide.md) before contributing to this project.

## License

[MIT License](LICENSE)
