"""
Reasoning Orchestrator for Hobbs Frontend.

Coordinates between Gemma 3 (conversation) and DeepCoder (reasoning).
Gemma decides when deep reasoning is needed - not hardcoded triggers.
"""

import json
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

from frontend.llm.ollama_client import ollama_client, LLMResponse
from config.settings import logger


# Model configuration - adjust based on what you have installed
GEMMA_MODEL = "gemma3"  # or "gemma:7b", "gemma2:9b", etc.
DEEPCODER_MODEL = "deepseek-coder"  # or "deepseek-coder:6.7b", "codellama", etc.


@dataclass
class ReasoningResult:
    """Result from the reasoning orchestrator."""
    user_response: str  # What Gemma says to the user
    reasoning_used: bool  # Whether DeepCoder was invoked
    reasoning_trace: Optional[str] = None  # DeepCoder's reasoning (if any)
    reasoning_summary: Optional[str] = None  # Gemma's summary of reasoning
    hobbs_data: Optional[Dict[str, Any]] = None  # Any Hobbs API data fetched
    model_used: str = ""
    reasoning_model: str = ""
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ReasoningOrchestrator:
    """
    Orchestrates conversation between user, Gemma 3, and DeepCoder.

    Flow:
    1. User sends message
    2. Gemma evaluates if deep reasoning is needed
    3. If yes: DeepCoder reasons, Gemma summarizes
    4. If no: Gemma responds directly
    """

    def __init__(
        self,
        gemma_model: str = GEMMA_MODEL,
        deepcoder_model: str = DEEPCODER_MODEL
    ):
        self.gemma_model = gemma_model
        self.deepcoder_model = deepcoder_model
        self.conversation_history: List[Dict[str, str]] = []
        self.hobbs_api_base = "http://localhost:5055"

        # System prompts
        self.gemma_system = """You are Hobbs Assistant, an AI helping manage a farm. You have access to:
- Sensor data (moisture, temperature, pH)
- Weather forecasts
- Security cameras for intruder detection
- Irrigation valve controls
- Historical patterns and learning insights

You can request deep reasoning from a specialized reasoning model when needed.
When you determine a question requires complex analysis, multi-step reasoning,
data correlation, or careful planning, output exactly: [NEED_REASONING]

Be helpful, concise, and farm-focused. If asked about data, you can query Hobbs systems."""

        self.reasoning_check_prompt = """Based on the user's message, determine if this requires deep reasoning.

Deep reasoning is needed for:
- Complex multi-step analysis
- Correlating multiple data sources
- Planning sequences of actions
- Debugging or troubleshooting
- Predictions requiring multiple factors
- Questions involving "why", "how would", "what if"
- Anything requiring careful step-by-step thinking

Simple responses (NO reasoning needed):
- Greetings and small talk
- Simple factual queries
- Status checks
- Direct commands
- Yes/no questions with obvious answers

User message: "{message}"

Respond with ONLY "REASON" or "DIRECT" (nothing else)."""

        self.deepcoder_system = """You are a reasoning engine for a farm management system called Hobbs.
Your job is to think through problems step-by-step, showing your work.

Available Hobbs data context:
{context}

Think carefully and systematically. Show your reasoning process.
Consider multiple angles and potential issues.
Be thorough but focused on the farming/agricultural context."""

        self.summarize_prompt = """The reasoning engine provided this analysis:

---
{reasoning}
---

Based on this reasoning, provide a clear, helpful response to the user.
Be concise but include the key insights from the reasoning.
The user wants to understand the conclusion and main points."""

    def should_use_reasoning(self, message: str) -> bool:
        """
        Ask Gemma if this message needs deep reasoning.
        This is the key - Gemma decides, not hardcoded rules.
        """
        prompt = self.reasoning_check_prompt.format(message=message)

        response = ollama_client.generate(
            model=self.gemma_model,
            prompt=prompt,
            temperature=0.1,  # Low temp for consistent classification
            max_tokens=10
        )

        decision = response.content.strip().upper()
        logger.info(f"Reasoning decision for '{message[:50]}...': {decision}")

        return "REASON" in decision

    def get_hobbs_context(self, message: str) -> Dict[str, Any]:
        """
        Fetch relevant data from Hobbs API based on the message.
        """
        import httpx

        context = {}

        try:
            with httpx.Client(timeout=10.0) as client:
                # Always get status
                status_resp = client.get(f"{self.hobbs_api_base}/status")
                if status_resp.status_code == 200:
                    context["status"] = status_resp.json()

                # Check if message mentions specific topics
                message_lower = message.lower()

                # Get learning report if asking about patterns/learning
                if any(word in message_lower for word in ["pattern", "learn", "trend", "baseline", "insight"]):
                    learn_resp = client.get(f"{self.hobbs_api_base}/learning_report")
                    if learn_resp.status_code == 200:
                        context["learning"] = learn_resp.json()

        except Exception as e:
            logger.warning(f"Failed to fetch Hobbs context: {e}")
            context["error"] = str(e)

        return context

    def invoke_deepcoder(self, message: str, context: Dict[str, Any]) -> str:
        """
        Have DeepCoder reason through the problem.
        """
        context_str = json.dumps(context, indent=2, default=str)

        system = self.deepcoder_system.format(context=context_str)

        prompt = f"""User question: {message}

Please reason through this step by step. Consider:
1. What data is relevant?
2. What are the key factors?
3. What conclusions can we draw?
4. What actions might be recommended?

Show your thinking process:"""

        response = ollama_client.generate(
            model=self.deepcoder_model,
            prompt=prompt,
            system=system,
            temperature=0.3,
            max_tokens=1000
        )

        return response.content

    def summarize_reasoning(self, reasoning: str, original_message: str) -> str:
        """
        Have Gemma summarize DeepCoder's reasoning for the user.
        """
        prompt = self.summarize_prompt.format(reasoning=reasoning)

        response = ollama_client.generate(
            model=self.gemma_model,
            prompt=prompt,
            system=f"Original user question: {original_message}",
            temperature=0.5,
            max_tokens=500
        )

        return response.content

    def direct_response(self, message: str, context: Dict[str, Any]) -> str:
        """
        Have Gemma respond directly without deep reasoning.
        """
        # Add context to conversation
        context_note = ""
        if context.get("status"):
            status = context["status"]
            context_note = f"\n\nCurrent Hobbs status: sensors_today={status.get('sensors_today', 0)}, " \
                          f"camera_events={status.get('camera_events_today', 0)}, " \
                          f"valves_known={status.get('valves_known', 0)}"

        # Build messages for chat
        messages = self.conversation_history.copy()
        messages.append({"role": "user", "content": message + context_note})

        response = ollama_client.chat(
            model=self.gemma_model,
            messages=messages,
            system=self.gemma_system,
            temperature=0.7
        )

        return response.content

    def process_message(self, message: str) -> ReasoningResult:
        """
        Main entry point - process a user message.

        Returns ReasoningResult with response and any reasoning trace.
        """
        # Check Ollama availability
        if not ollama_client.is_available():
            return ReasoningResult(
                user_response="I'm unable to connect to the AI models. Please ensure Ollama is running.",
                reasoning_used=False,
                model_used="none"
            )

        # Get Hobbs context
        context = self.get_hobbs_context(message)

        # Ask Gemma if we need reasoning
        needs_reasoning = self.should_use_reasoning(message)

        if needs_reasoning:
            logger.info("Invoking DeepCoder for reasoning...")

            # Get DeepCoder reasoning
            reasoning_trace = self.invoke_deepcoder(message, context)

            # Have Gemma summarize
            user_response = self.summarize_reasoning(reasoning_trace, message)

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": user_response})

            return ReasoningResult(
                user_response=user_response,
                reasoning_used=True,
                reasoning_trace=reasoning_trace,
                reasoning_summary=user_response,
                hobbs_data=context,
                model_used=self.gemma_model,
                reasoning_model=self.deepcoder_model
            )

        else:
            logger.info("Direct response (no reasoning needed)")

            # Direct response from Gemma
            user_response = self.direct_response(message, context)

            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": user_response})

            return ReasoningResult(
                user_response=user_response,
                reasoning_used=False,
                hobbs_data=context,
                model_used=self.gemma_model
            )

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def get_model_status(self) -> Dict[str, Any]:
        """Get status of available models."""
        available = ollama_client.is_available()
        models = ollama_client.list_models() if available else []

        return {
            "ollama_available": available,
            "models_available": models,
            "gemma_model": self.gemma_model,
            "deepcoder_model": self.deepcoder_model,
            "gemma_ready": self.gemma_model in models or any(self.gemma_model in m for m in models),
            "deepcoder_ready": self.deepcoder_model in models or any(self.deepcoder_model in m for m in models)
        }


# Singleton instance
reasoning_orchestrator = ReasoningOrchestrator()
