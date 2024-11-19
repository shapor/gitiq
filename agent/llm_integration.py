"""
llm_integration.py - Simple LLM integration supporting multiple providers
"""
import os
import re
import json
import logging
import importlib
from typing import Dict, List, Optional, Union
from queue import Queue

import openai
import anthropic
from anthropic import Anthropic
import tiktoken

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - level=%(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Module level config
_llm_apis = None
_models = None
_last_api_base = None

def load_llm_config(config_path: str) -> None:
    """Load LLM configuration from a JSON file."""
    global _llm_apis, _models
    with open(config_path) as f:
        config = json.load(f)
    _llm_apis = config['llm_apis']
    _models = config['models']

def list_models():
    """Returns list of available model names."""
    if _models is None:
        raise RuntimeError("Call load_llm_config before using list_models")
    return list(_models.keys())

def _ensure_openai_configured(api_base: str, api_key: str) -> None:
    """Ensure OpenAI is configured correctly for the current request."""
    global _last_api_base
    if _last_api_base != api_base:
        os.environ["OPENAI_API_BASE"] = api_base
        importlib.reload(openai)
        _last_api_base = api_base
    openai.api_key = api_key

def _format_messages_for_claude(messages: List[Dict[str, str]]) -> tuple[str, List[Dict]]:
    """Format messages for Claude API, separating system message."""
    system_message = next((m["content"] for m in messages if m["role"] == "system"), "")
    user_messages = [m for m in messages if m["role"] != "system"]
    return system_message, user_messages

def calculate_cost(prompt_tokens: int, completion_tokens: int, model_name: str) -> float:
    """
    Calculate the cost of an API call based on token usage and model pricing.

    Args:
        prompt_tokens: Number of tokens in the prompt
        completion_tokens: Number of tokens in the completion
        model_name: Name of the model used

    Returns:
        Total cost in USD
    """
    if _models is None:
        raise RuntimeError("Call load_llm_config before using calculate_cost")
    model = _models.get(model_name)
    if not model:
        logger.warning(f"Model {model_name} not found in configuration. Cannot calculate cost.")
        return 0.0
    cost = model.get('cost', [0, 0])
    cost_total = (prompt_tokens * cost[0] + completion_tokens * cost[1]) / 1000
    return cost_total

def chat_completion(
    messages: List[Dict[str, str]],
    model_name: str,
    stats_queue: Optional[Queue] = None,
    extract_code_block: bool = False,
    json_output: bool = False,
    **kwargs
) -> Union[str, Dict]:
    """
    Create a chat completion using the specified model.

    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model_name: Name of the model to use from config
        stats_queue: Optional queue to collect usage statistics
        extract_code_block: Whether to extract content from code blocks
        json_output: Whether to parse the output as JSON
        **kwargs: Additional arguments to pass to the API

    Returns:
        The completion text or parsed JSON object
    """
    if _llm_apis is None or _models is None:
        raise RuntimeError("Call load_llm_config before using chat_completion")

    logger.debug(f"LLM Input:\n{messages}\nLLM Metadata: {kwargs}")
    
    model = _models.get(model_name)
    if not model:
        logger.error(f"Model {model_name} not found in configuration")
        raise ValueError(f"Model {model_name} not found.")
    max_output_tokens = model.get('max_output_tokens', 4000)
    if not model.get('nojson', False) and json_output:
        kwargs['response_format'] = {"type": "json_object"}
    api_config = _llm_apis[model['llm_api']]
    api_type = api_config.get('api_type', 'openai')

    if api_type == 'openai':
        _ensure_openai_configured(api_config['api_base'], os.getenv(api_config['api_key']))
        response = openai.ChatCompletion.create(
            model=model['name'],
            messages=messages,
            max_tokens=max_output_tokens,
            n=1,
            stop=None,
            temperature=0.1,
            **kwargs
        )
        llm_output = response.choices[0].message.content.strip()
        # Calculate cost in USD
        cost_total = calculate_cost(
            response.usage.prompt_tokens,
            response.usage.completion_tokens,
            model_name
        )
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": cost_total
        }

    elif api_type == 'anthropic':
        system_message, user_messages = _format_messages_for_claude(messages)
        client = Anthropic(api_key=os.getenv(api_config['api_key']))
        response = client.completions.create(
            model=model['name'],
            max_tokens_to_sample=max_output_tokens,
            prompt=anthropic.HUMAN_PROMPT + system_message + "\n\n" + "\n\n".join([m['content'] for m in user_messages]) + anthropic.AI_PROMPT,
            temperature=0.1,
            **kwargs
        )
        llm_output = response.completion.strip()
        # As Anthropic API does not return usage, we may not be able to calculate cost accurately
        prompt_tokens = count_tokens(response.prompt)
        completion_tokens = count_tokens(response.completion)
        cost_total = calculate_cost(
            prompt_tokens,
            completion_tokens,
            model_name
        )
        usage = {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "cost": cost_total
        }
    else:
        raise ValueError(f"Unsupported API type: {api_type}")

    logger.debug(f"Usage: {usage}\nLLM Output: {llm_output}")
    
    if stats_queue is not None:
        stats_queue.put(usage)

    # Handle model-specific output manipulation
    if "Reflection" in model['name']:
        match = re.search(r'<output>(.*)</output>', llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            llm_output = match.group(1)
            logger.debug(f"Extracted LLM Output: {llm_output}")

    # If extract_code_block is set, extract code block
    if extract_code_block:
        match = re.search(r'```(?:[a-z]+)?\n([\s\S]*?)\n```', llm_output)
        if match:
            llm_output = match.group(1).strip()
            logger.debug(f"Extracted from code block: {llm_output}")
        else:
            # Attempt to extract content even if code fences are not properly formatted
            llm_output = llm_output.strip('`').strip()
            logger.debug(f"Stripped code fences: {llm_output}")

    if json_output:
        try:
            parsed_output = json.loads(llm_output, strict=False)
            return parsed_output
        except json.JSONDecodeError:
            logger.debug("Failed to parse JSON, attempting to extract JSON from code block")
            # If extract_code_block was not set, we can try again
            if not extract_code_block:
                match = re.search(r'```(?:json)?\n([\s\S]*?)```', llm_output)
                if match:
                    json_content = match.group(1)
                    try:
                        parsed_output = json.loads(json_content, strict=False)
                        return parsed_output
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse JSON response from code block: {llm_output}")
                        raise ValueError("Invalid JSON response from LLM")
            logger.error(f"Failed to parse JSON response: {llm_output}")
            raise ValueError("Invalid JSON response from LLM")
    else:
        return llm_output

def count_tokens(text: str, model_name: str = "gpt-3.5-turbo") -> int:
    """
    Count the number of tokens in a given text using the specified model's tokenizer.
    
    Args:
        text: The input text to tokenize
        model_name: The name of the model to use for tokenization (default: gpt-3.5-turbo)
        
    Returns:
        The number of tokens in the text
    """
    try:
        encoding = tiktoken.encoding_for_model(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    
    return len(encoding.encode(text))
