"""
llm_integration.py - Simple LLM integration supporting multiple providers
"""
import os
import re
import json
import logging
import importlib
from typing import Dict, List, Optional
from queue import Queue

import openai
import anthropic
from anthropic import Anthropic

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

def chat_completion(
    messages: List[Dict[str, str]], 
    model_name: str,
    stats_queue: Optional[Queue] = None,
    extract_code_block: bool = False,
    json_output: bool = False,
    **kwargs
) -> str:
    """
    Create a chat completion using the specified model.
    
    Args:
        messages: List of message dictionaries with 'role' and 'content'
        model_name: Name of the model to use from config
        stats_queue: Optional queue to collect usage statistics
        extract_code_block: Whether to extract content from code blocks
        **kwargs: Additional arguments to pass to the API
        
    Returns:
        The completion text
    """
    if _llm_apis is None or _models is None:
        raise RuntimeError("Call load_llm_config before using chat_completion")

    logger.debug(f"LLM Input:\n{messages}\nLLM Metadata: {kwargs}")
    
    model = _models[model_name]
    if not model.get('nojson', False) and json_output:
        kwargs['response_format'] = {"type": "json_object"}
    api_config = _llm_apis[model['llm_api']]
    api_type = api_config.get('api_type', 'openai')
    cost = model.get('cost', [0, 0])

    if api_type == 'openai':
        _ensure_openai_configured(api_config['api_base'], os.getenv(api_config['api_key']))
        response = openai.ChatCompletion.create(
            model=model['name'],
            messages=messages,
            max_tokens=8192,
            n=1,
            stop=None,
            temperature=0.1,
            **kwargs
        )
        llm_output = response.choices[0].message.content.strip()
        usage = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "cost": response.usage.prompt_tokens * cost[0] + response.usage.completion_tokens * cost[1]
        }

    elif api_type == 'anthropic':
        system_message, user_messages = _format_messages_for_claude(messages)
        response = anthropic.Anthropic(api_key=os.getenv(api_config['api_key'])).messages.create(
            model=model['name'],
            system=system_message,
            messages=user_messages,
            max_tokens=8192,  # Required by Anthropic
            temperature=0.1,
            **kwargs
        )
        llm_output = response.content[0].text
        usage = {
            "prompt_tokens": response.usage.input_tokens,
            "completion_tokens": response.usage.output_tokens,
            "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            "cost": (response.usage.input_tokens * cost[0] + response.usage.output_tokens * cost[1]) / 1000
        }
    else:
        raise ValueError(f"Unsupported API type: {api_type}")

    logger.debug(f"Usage: {usage}\nLLM Output: {llm_output}")
    
    if stats_queue is not None:
        stats_queue.put(usage)

    if "Reflection" in model['name']:
        match = re.search(r'<output>(.*)</output>', llm_output, re.DOTALL | re.IGNORECASE)
        if match:
            llm_output = match.group(1)
            logger.debug(f"Extracted LLM Output: {llm_output}")

    if extract_code_block:
        match = re.search(r'```(?:[a-z]+)?\n([\s\S]*?)\n```', llm_output)
        if match:
            llm_output = match.group(1).strip()
            logger.debug(f"Extracted from code block: {llm_output}")

    return llm_output
