"""
Ollama Client for local LLM integration.

Connects to Ollama running locally for Gemma 3 (conversation) and DeepCoder (reasoning).
"""

import json
import httpx
from typing import Generator, Optional, Dict, Any, List
from dataclasses import dataclass
from config.settings import logger


OLLAMA_BASE_URL = "http://localhost:11434"


@dataclass
class LLMResponse:
    """Response from an LLM call."""
    content: str
    model: str
    done: bool
    total_duration: Optional[int] = None
    eval_count: Optional[int] = None


class OllamaClient:
    """
    Client for interacting with Ollama API.

    Supports both streaming and non-streaming responses.
    """

    def __init__(self, base_url: str = OLLAMA_BASE_URL):
        self.base_url = base_url
        self.timeout = httpx.Timeout(120.0, connect=10.0)

    def is_available(self) -> bool:
        """Check if Ollama is running and accessible."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """List available models in Ollama."""
        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
        except Exception as e:
            logger.error(f"Failed to list Ollama models: {e}")
        return []

    def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        context: Optional[List[int]] = None,
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None
    ) -> LLMResponse:
        """
        Generate a response from a model.

        Args:
            model: Model name (e.g., "gemma3", "deepseek-coder")
            prompt: User prompt
            system: System prompt
            context: Previous context for conversation continuity
            stream: Whether to stream the response
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate

        Returns:
            LLMResponse with generated content
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,  # We'll handle streaming separately
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            payload["system"] = system
        if context:
            payload["context"] = context
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    return LLMResponse(
                        content=data.get("response", ""),
                        model=model,
                        done=data.get("done", True),
                        total_duration=data.get("total_duration"),
                        eval_count=data.get("eval_count")
                    )
                else:
                    logger.error(f"Ollama error: {response.status_code} - {response.text}")
                    return LLMResponse(
                        content=f"Error: {response.status_code}",
                        model=model,
                        done=True
                    )

        except Exception as e:
            logger.error(f"Ollama request failed: {e}")
            return LLMResponse(
                content=f"Error connecting to Ollama: {str(e)}",
                model=model,
                done=True
            )

    def generate_stream(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> Generator[str, None, None]:
        """
        Stream a response from a model.

        Yields chunks of text as they're generated.
        """
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=self.timeout) as client:
                with client.stream(
                    "POST",
                    f"{self.base_url}/api/generate",
                    json=payload
                ) as response:
                    for line in response.iter_lines():
                        if line:
                            try:
                                data = json.loads(line)
                                if "response" in data:
                                    yield data["response"]
                                if data.get("done"):
                                    break
                            except json.JSONDecodeError:
                                continue

        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            yield f"Error: {str(e)}"

    def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7
    ) -> LLMResponse:
        """
        Chat completion with message history.

        Args:
            model: Model name
            messages: List of {"role": "user"|"assistant", "content": "..."}
            system: System prompt
            temperature: Sampling temperature

        Returns:
            LLMResponse with assistant's reply
        """
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        if system:
            # Prepend system message
            payload["messages"] = [{"role": "system", "content": system}] + messages

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    message = data.get("message", {})
                    return LLMResponse(
                        content=message.get("content", ""),
                        model=model,
                        done=data.get("done", True),
                        total_duration=data.get("total_duration"),
                        eval_count=data.get("eval_count")
                    )
                else:
                    return LLMResponse(
                        content=f"Error: {response.status_code}",
                        model=model,
                        done=True
                    )

        except Exception as e:
            logger.error(f"Ollama chat failed: {e}")
            return LLMResponse(
                content=f"Error: {str(e)}",
                model=model,
                done=True
            )


# Singleton instance
ollama_client = OllamaClient()
