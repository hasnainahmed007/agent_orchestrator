"""Multi-LLM provider support for different AI backends.

Supports: OpenAI, Anthropic (Claude), Google (Gemini), Ollama (local), and
any OpenAI-compatible endpoint (OpenRouter, Moonshot, DeepSeek, etc.).
"""
import os
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

# Provider registry
LLM_PROVIDERS: dict[str, callable] = {}


def register_provider(name: str):
    """Decorator to register an LLM provider factory."""
    def wrapper(fn):
        LLM_PROVIDERS[name] = fn
        return fn
    return wrapper


def create_llm(provider: str = "openai", model: str = "gpt-4o",
               api_key: str = "", base_url: str = "",
               temperature: float = 0.1, max_tokens: int = 4000,
               **kwargs) -> Any:
    """Create an LLM instance for CrewAI.

    Args:
        provider: One of 'openai', 'anthropic', 'google', 'ollama', 'auto'
        model: Model name/ID
        api_key: API key (reads from env if not provided)
        base_url: Custom base URL for OpenAI-compatible endpoints
        temperature: Temperature for generation
        max_tokens: Max tokens per response

    Returns:
        CrewAI-compatible LLM instance, or str model name for OpenAI shortcut.
    """
    if provider in LLM_PROVIDERS:
        return LLM_PROVIDERS[provider](model, api_key, base_url, temperature, max_tokens, **kwargs)

    # Fallback: try as OpenAI-compatible endpoint
    logger.warning(f"Unknown provider '{provider}', falling back to OpenAI-compatible mode")
    return _create_openai_compatible(model, api_key, base_url, temperature, max_tokens, **kwargs)


def _create_openai_compatible(model: str, api_key: str, base_url: str,
                               temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create an OpenAI-compatible LLM instance."""
    api_key = api_key or os.getenv('OPENAI_API_KEY', '')
    base_url = base_url or os.getenv('OPENAI_BASE_URL', '')

    # For CrewAI 1.14, pass model name string + set env for base_url
    # CrewAI's OpenAICompletion reads OPENAI_BASE_URL automatically
    if base_url:
        os.environ.setdefault('OPENAI_BASE_URL', base_url)

    # Return model name as string — CrewAI handles the rest
    return model


@register_provider('openai')
def _create_openai(model: str, api_key: str, base_url: str,
                   temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create OpenAI LLM via CrewAI native string mode."""
    api_key = api_key or os.getenv('OPENAI_API_KEY', '')
    base_url = base_url or os.getenv('OPENAI_BASE_URL', '')

    if base_url:
        os.environ.setdefault('OPENAI_BASE_URL', base_url)
    if api_key:
        os.environ.setdefault('OPENAI_API_KEY', api_key)

    return model  # CrewAI auto-creates OpenAI LLM


@register_provider('anthropic')
def _create_anthropic(model: str, api_key: str, base_url: str,
                      temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create Anthropic Claude LLM for CrewAI."""
    api_key = api_key or os.getenv('ANTHROPIC_API_KEY', '')

    try:
        # CrewAI 1.14 may support anthropic natively
        return f"anthropic/{model}"
    except Exception:
        pass

    # Fallback: Use crewai's BaseLLM if available
    try:
        from crewai.llms.providers.anthropic.completion import AnthropicCompletion
        return AnthropicCompletion(
            model=model,
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    except ImportError:
        logger.warning("Anthropic provider not available in CrewAI. Install: pip install crewai[anthropic]")
        return model


@register_provider('google')
def _create_google(model: str, api_key: str, base_url: str,
                   temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create Google Gemini LLM for CrewAI."""
    api_key = api_key or os.getenv('GOOGLE_API_KEY', '') or os.getenv('GEMINI_API_KEY', '')

    try:
        from crewai.llms.providers.gemini.completion import GeminiCompletion
        return GeminiCompletion(
            model=model or "gemini-pro",
            api_key=api_key,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    except ImportError:
        logger.warning("Gemini provider not available. Install: pip install google-generativeai")
        return model


@register_provider('ollama')
def _create_ollama(model: str, api_key: str, base_url: str,
                   temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create local Ollama LLM for CrewAI."""
    host = base_url or os.getenv('OLLAMA_HOST', 'http://localhost:11434')

    try:
        from crewai.llms.providers.ollama.completion import OllamaCompletion
        return OllamaCompletion(
            model=model or "llama3",
            base_url=host,
            temperature=temperature,
            max_tokens=max_tokens,
            **kwargs
        )
    except ImportError:
        logger.warning("Ollama provider not available natively. Using OpenAI-compatible mode.")
        # Ollama has OpenAI-compatible API at /v1
        return _create_openai_compatible(model, "ollama", f"{host}/v1",
                                         temperature, max_tokens, **kwargs)


@register_provider('deepseek')
def _create_deepseek(model: str, api_key: str, base_url: str,
                     temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create DeepSeek LLM (OpenAI-compatible)."""
    api_key = api_key or os.getenv('DEEPSEEK_API_KEY', '')
    base_url = base_url or "https://api.deepseek.com/v1"
    return _create_openai_compatible(model, api_key, base_url, temperature, max_tokens, **kwargs)


@register_provider('groq')
def _create_groq(model: str, api_key: str, base_url: str,
                 temperature: float, max_tokens: int, **kwargs) -> Any:
    """Create Groq LLM (OpenAI-compatible)."""
    api_key = api_key or os.getenv('GROQ_API_KEY', '')
    base_url = base_url or "https://api.groq.com/openai/v1"
    return _create_openai_compatible(model, api_key, base_url, temperature, max_tokens, **kwargs)


def detect_provider_from_model(model: str) -> str:
    """Auto-detect provider from model name."""
    model_lower = model.lower()
    if 'claude' in model_lower:
        return 'anthropic'
    if 'gemini' in model_lower:
        return 'google'
    if 'llama' in model_lower or 'mistral' in model_lower or 'codellama' in model_lower:
        return 'ollama'
    if 'deepseek' in model_lower:
        return 'deepseek'
    return 'openai'


def get_available_providers() -> list[str]:
    """Return list of registered provider names."""
    return list(LLM_PROVIDERS.keys())
