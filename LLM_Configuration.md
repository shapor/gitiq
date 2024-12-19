# LLM Configuration

## Overview

GitIQ relies on Large Language Models (LLMs) to generate code changes based on user prompts. The LLMs are configured via the `config.json` file. This guide explains how to set up and customize the LLM integrations.

## LLM APIs Configuration

The `llm_apis` section in `config.json` defines the available LLM API endpoints and their authentication:

```json
{
  "llm_apis": {
    "openai": {
      "api_base": "https://api.openai.com/v1",
      "api_key": "OPENAI_API_KEY"
    },
    "claude": {
      "api_type": "anthropic",
      "api_key": "ANTHROPIC_API_KEY"
    },
    "together": {
      "api_base": "https://api.together.ai/v1",
      "api_key": "TOGETHER_API_KEY"
    }
  }
}
```

Each LLM API configuration includes:

- `api_base`: The base URL for the API endpoint.
- `api_key`: The environment variable name containing the API key.
- `api_type`: Special handler for non-OpenAI compatible APIs (e.g., `"anthropic"` for models like Claude).

Ensure that the environment variables specified in `api_key` are set in your system with the actual API keys.

## Models Configuration

The `models` section defines the available models and their specific configurations:

```json
{
  "models": {
    "GPT-4 Turbo": {
      "llm_api": "openai",
      "name": "gpt-4-turbo",
      "cost": [0.01, 0.03],
      "max_output_tokens": 4096,
      "temperature": 0.1
    },
    "Claude 3.5": {
      "llm_api": "claude",
      "name": "claude-3-5",
      "nojson": true,
      "max_output_tokens": 8192,
      "cost": [0.003, 0.015],
      "temperature": 0.1
    }
  }
}
```

Each model configuration includes:

- `llm_api`: References which API configuration to use from `llm_apis`. This tells GitIQ which API to use when making requests for this model.
- `name`: The model identifier used in API calls. This must match the model name expected by the API.
- `cost`: An array of `[prompt_cost, completion_cost]` per 1000 tokens. This is used for tracking usage costs.
- `max_output_tokens`: The maximum number of tokens the model will generate in a response.
- `temperature`: Controls the randomness of the output. A lower value results in more deterministic output.
- `nojson` (optional): Set to `true` if the model does not support JSON responses directly.
- `nosystem` (optional): Set to `true` if the model does not support system messages.
- `max_tokens_parameter` (optional): Override parameter name for max tokens (e.g., `"max_completion_tokens"` for certain models).

## Setting Up LLM APIs

1. **Obtain API Keys**: Sign up for the LLM services you intend to use (e.g., OpenAI, Anthropic) and obtain API keys.
2. **Set Environment Variables**: Export the API keys as environment variables on your system. For example:
   ```bash
   export OPENAI_API_KEY=your_openai_api_key
   export ANTHROPIC_API_KEY=your_anthropic_api_key
   ```
3. **Configure `config.json`**: Update the `llm_apis` section with the API base URLs and the environment variable names containing the API keys.

## Selecting Models

- In the `models` section, you can define multiple models and their configurations.
- Ensure that the `llm_api` field matches one of the entries in the `llm_apis` section.
- Adjust `max_output_tokens`, `temperature`, and other parameters based on your requirements and the capabilities of the model.

## Example Configuration

An example `config.json` might look like:

```json
{
  "llm_apis": {
    "openai": {
      "api_base": "https://api.openai.com/v1",
      "api_key": "OPENAI_API_KEY"
    }
  },
  "models": {
    "GPT-4": {
      "llm_api": "openai",
      "name": "gpt-4",
      "cost": [0.03, 0.06],
      "max_output_tokens": 8192,
      "temperature": 0.7
    }
  }
}
```

## Tips

- **Environment Variables**: Always keep your API keys secure. Do not hard-code them into configuration files.
- **Model Limits**: Be aware of the token limits and capabilities of your chosen models to avoid errors.
- **Cost Tracking**: Setting the `cost` field helps you keep track of your API usage expenses.
