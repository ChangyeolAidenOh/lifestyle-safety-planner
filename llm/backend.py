"""Unified LLM backend with automatic fallback.

Primary: Ollama (Qwen 2.5 7B) - zero cost, local
Fallback: Anthropic Haiku - low cost, cloud
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMBackend(ABC):
    """Abstract base for LLM backends."""

    @abstractmethod
    def generate(self, prompt, system=None, temperature=0.3, max_tokens=1024):
        """Generate text completion."""
        pass

    @abstractmethod
    def is_available(self):
        """Check if this backend is reachable."""
        pass


class OllamaBackend(LLMBackend):
    """Local Ollama backend (Qwen 2.5 7B)."""

    def __init__(self, base_url, model):
        self.base_url = base_url
        self.model = model

    def generate(self, prompt, system=None, temperature=0.3, max_tokens=1024):
        import ollama
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = ollama.chat(
            model=self.model,
            messages=messages,
            options={"temperature": temperature, "num_predict": max_tokens},
        )
        return response["message"]["content"]

    def is_available(self):
        try:
            import ollama
            ollama.list()
            return True
        except Exception as e:
            logger.warning("Ollama not available: %s", e)
            return False


class AnthropicBackend(LLMBackend):
    """Anthropic Haiku fallback backend."""

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model

    def generate(self, prompt, system=None, temperature=0.3, max_tokens=1024):
        import anthropic
        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text

    def is_available(self):
        return bool(self.api_key)


class LLMRouter:
    """Routes to available LLM backend with automatic fallback.

    Usage:
        router = LLMRouter.from_config()
        result = router.generate("Explain the safety profile.")
    """

    def __init__(self, primary, fallback=None):
        self.primary = primary
        self.fallback = fallback
        self._active = None

    @classmethod
    def from_config(cls):
        """Build router from config.py settings."""
        from config import (
            LLM_BACKEND, OLLAMA_BASE_URL, OLLAMA_MODEL,
            ANTHROPIC_API_KEY, ANTHROPIC_MODEL,
        )
        ollama_be = OllamaBackend(OLLAMA_BASE_URL, OLLAMA_MODEL)
        anthropic_be = AnthropicBackend(ANTHROPIC_API_KEY, ANTHROPIC_MODEL)

        if LLM_BACKEND == "anthropic":
            return cls(primary=anthropic_be, fallback=ollama_be)
        return cls(primary=ollama_be, fallback=anthropic_be)

    def generate(self, prompt, system=None, temperature=0.3, max_tokens=1024):
        """Generate with automatic fallback."""
        # Try primary
        if self.primary.is_available():
            try:
                self._active = "primary"
                return self.primary.generate(
                    prompt, system, temperature, max_tokens
                )
            except Exception as e:
                logger.warning("Primary LLM failed: %s", e)

        # Fallback
        if self.fallback and self.fallback.is_available():
            try:
                self._active = "fallback"
                logger.info("Falling back to secondary LLM backend.")
                return self.fallback.generate(
                    prompt, system, temperature, max_tokens
                )
            except Exception as e:
                logger.error("Fallback LLM also failed: %s", e)

        self._active = None
        return None

    @property
    def active_backend(self):
        """Return which backend was used in the last call."""
        return self._active
