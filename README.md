# GitIQ

GitIQ is an AI-powered pair programming tool that leverages Git as the primary interface, enabling seamless collaboration without the need for embedding in an IDE. With GitIQ, developers can describe changes in natural language and receive complete Pull Requests, enhancing productivity and simplifying the development workflow.

## Table of Contents

- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Git Configuration](#git-configuration)
  - [LLM API Configuration](#llm-api-configuration)
  - [Model Configuration](#model-configuration)
- [Usage](#usage)
- [Documentation](#documentation)
- [Contributing](#contributing)

## Features

- **Git Integration**: Uses Git as the primary interface, allowing for seamless integration into existing workflows.
- **AI-Powered Code Changes**: Transforms natural language descriptions into complete Pull Requests.
- **Context Preservation**: Maintains a clear history of AI-human collaboration through Git commits.
- **Multi-File Support**: Handles changes across multiple files as coherent units of work.
- **Reviewable PRs**: Generates PRs that can be reviewed and merged, fitting into standard code review processes.
- **Flexible Configuration**: Supports multiple LLM providers and models through easy-to-edit configuration files.
- **IDE Agnostic**: Works with any editor or IDE since changes flow through Git.
- **GitHub Integration**: Optionally integrates with GitHub to automatically create Pull Requests.

## Quick Start

To get started with GitIQ, follow these steps:

### Prerequisites

- **Python 3.7 or higher**: Ensure Python is installed on your system.
- **Git**: Git must be installed and configured.
- **OpenAI API Key**: An API key for OpenAI or other supported LLM providers.
- **GitHub Access Token**: Required if you want to enable GitHub integration.

### Installation

Clone the repository:

```bash
git clone https://github.com/yourusername/gitiq.git
cd gitiq
```

Install the required Python packages:

```bash
pip install -r requirements.txt
```

### Running the Application

Set your API key and run the application:

```bash
export OPENAI_API_KEY=your_api_key_here
python agent/app.py
```

Alternatively, you can run the application with the API key inline:

```bash
OPENAI_API_KEY=your_api_key_here python agent/app.py
```

## Configuration

GitIQ uses a `config.json` file for various settings. Below is an overview of the configuration options.

### Git Configuration

```json
"git": {
  "name": "GitIQ Bot",
  "email": "gitiq-bot@gmail.com"
}
```

Set the Git user name and email for commits made by GitIQ.

### LLM API Configuration

```json
"llm_apis": {
  "openai": {
    "api_base": "https://api.openai.com/v1",
    "api_key": "OPENAI_API_KEY"
  },
  "lmproxy": {
    "api_base": "https://api.lmproxy.org/v1",
    "api_key": "OPENAI_API_KEY"
  }
}
```

Define the LLM API endpoints and their corresponding API keys. API keys are specified as environment variable names.

### Model Configuration

```json
"models": {
  "Claude 3.5 Sonnet": {
    "llm_api": "claude",
    "name": "claude-3-5-sonnet-20240620",
    "nojson": true
  },
  "OpenAI o1-preview (via OpenRouter)": {
    "llm_api": "openrouter",
    "name": "openai/o1-preview"
  }
}
```

Define the available models, specifying which API to use, the model name, and any special flags like `nojson` for models that don't support JSON output.

### GitHub Integration

To enable GitHub integration, update the `config.json` file:

```json
"github": {
  "enabled": true,
  "access_token": "GITHUB_ACCESS_TOKEN",
  "repo_owner": "your_github_username",
  "repo_name": "your_repository_name"
}
```

- **enabled**: Set to `true` to enable GitHub integration.
- **access_token**: Your GitHub access token, stored as an environment variable.
- **repo_owner**: The owner of the repository.
- **repo_name**: The name of the repository.

## Usage

Once the application is running, you can start using GitIQ to assist with your coding tasks. Describe the changes you want to make in natural language, and GitIQ will generate the corresponding code changes and create a Pull Request for your review.

## Documentation

For more detailed information, please refer to the following documents:

- [Product Requirements Document](PRD.md): Detailed requirements and specifications.
- [API Specification](API.md): Information about the API endpoints and usage.
- [Style Guide](Style_Guide.md): Guidelines for contributing to the project.

## Contributing

We welcome contributions! Please read our [Style Guide](Style_Guide.md) before contributing to ensure consistency in the codebase. You can contribute by submitting Pull Requests, reporting issues, or suggesting new features.

