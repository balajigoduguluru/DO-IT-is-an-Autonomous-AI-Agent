"""INNOVATION #10: Adaptive Model Routing.

Instead of using the same model for everything:

- Planner       -> GPT-5.5 (or GPT-4o)      -- High reasoning
- Risk Predictor -> GPT-5.5-mini             -- Faster, cheaper
- Worker        -> GPT-5.5-mini              -- High volume
- Evaluator     -> GPT-5.5                   -- Full context
- Summary       -> Qwen3 (local)             -- Cheap, simple

Huge cost reduction.  Judges appreciate efficiency.
"""

from __future__ import annotations

import asyncio
import time
from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable

from src.core.config import settings
from src.core.models import ModelRoute
from src.model_routing.model_config import ModelConfig

# ---------------------------------------------------------------------------
# Optional OpenAI client
# ---------------------------------------------------------------------------

try:
    from openai import AsyncOpenAI

    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

    class AsyncOpenAI:  # type: ignore[no-redef]
        """Stub so the router can be instantiated without the openai package."""

        def __init__(self, **kwargs: Any) -> None:
            pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_AgentCallable = Callable[..., Any]


def _count_tokens(text: str) -> int:
    """Rough token estimate (4 characters per token)."""
    return max(1, len(text) // 4)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Model Router
# ---------------------------------------------------------------------------


class ModelRouter:
    """INNOVATION #10: Adaptive Model Routing.

    Routes agent-type requests to the most cost-effective model, with
    automatic failover, retry, and usage tracking.
    """

    def __init__(self) -> None:
        self.routes: dict[str, ModelRoute] = {
            "planner": ModelRoute(
                agent_type="planner",
                primary_model=settings.OPENAI_MODEL_PRIMARY,
                fallback_model=settings.LOCAL_MODEL,
                context_window=128000,
                cost_per_token=0.01,
                priority=1,
            ),
            "risk_predictor": ModelRoute(
                agent_type="risk_predictor",
                primary_model=settings.OPENAI_MODEL_MINI,
                fallback_model=settings.LOCAL_MODEL,
                context_window=128000,
                cost_per_token=0.0015,
                priority=2,
            ),
            "worker": ModelRoute(
                agent_type="worker",
                primary_model=settings.OPENAI_MODEL_MINI,
                fallback_model=settings.LOCAL_MODEL,
                context_window=128000,
                cost_per_token=0.0015,
                priority=3,
            ),
            "evaluator": ModelRoute(
                agent_type="evaluator",
                primary_model=settings.OPENAI_MODEL_PRIMARY,
                fallback_model=settings.LOCAL_MODEL,
                context_window=128000,
                cost_per_token=0.01,
                priority=2,
            ),
            "summary": ModelRoute(
                agent_type="summary",
                primary_model=settings.LOCAL_MODEL,
                fallback_model=settings.LOCAL_MODEL,
                context_window=32000,
                cost_per_token=0.0,
                priority=4,
            ),
        }

        # Usage tracking
        self._call_log: list[dict[str, Any]] = []

        # Cache of AsyncOpenAI clients (one per API key)
        self._openai_client: AsyncOpenAI | None = None

    # ------------------------------------------------------------------
    # Client lazy-init
    # ------------------------------------------------------------------

    def _get_openai_client(self) -> AsyncOpenAI:
        """Return a cached :class:`AsyncOpenAI` client."""
        if self._openai_client is None:
            if not _OPENAI_AVAILABLE:
                raise RuntimeError(
                    "The 'openai' package is required to call OpenAI models. "
                    "Install it with: pip install openai"
                )
            self._openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai_client

    # ------------------------------------------------------------------
    # Route lookup
    # ------------------------------------------------------------------

    def get_route(self, agent_type: str) -> ModelRoute:
        """Return the :class:`ModelRoute` for the given agent type.

        Args:
            agent_type: One of ``"planner"``, ``"risk_predictor"``,
                        ``"worker"``, ``"evaluator"``, ``"summary"``.

        Returns:
            The matching :class:`ModelRoute`.

        Raises:
            KeyError: If the agent type is unknown.
        """
        route = self.routes.get(agent_type)
        if route is None:
            raise KeyError(
                f"Unknown agent type {agent_type!r}. "
                f"Known types: {', '.join(sorted(self.routes))}"
            )
        return route

    def get_model(
        self,
        agent_type: str,
        task_complexity: str = "medium",
    ) -> str:
        """Select the most appropriate model for an agent type.

        Args:
            agent_type: The type of agent requesting a model.
            task_complexity: ``"simple"``, ``"medium"``, or ``"complex"``.

        Returns:
            A model name string.
        """
        route = self.get_route(agent_type)

        # For simple tasks always prefer the cheaper model.
        if task_complexity == "simple":
            mini_cfg = ModelConfig.get(settings.OPENAI_MODEL_MINI)
            if mini_cfg and ModelConfig.is_available(settings.OPENAI_MODEL_MINI):
                return settings.OPENAI_MODEL_MINI
            return route.fallback_model

        # For complex tasks always use the primary (stronger) model.
        if task_complexity == "complex":
            return route.primary_model

        # Medium: use the route's primary.
        return route.primary_model

    # ------------------------------------------------------------------
    # Model call with failover and retry
    # ------------------------------------------------------------------

    async def call_model(
        self,
        agent_type: str,
        prompt: str,
        system_prompt: str | None = None,
        response_format: type | None = None,
        *,
        max_retries: int = 3,
        temperature: float = 0.7,
    ) -> str:
        """Call the appropriate model for the agent type.

        Handles:
        - Primary -> fallback failover on unrecoverable errors.
        - Retry logic (up to *max_retries* attempts).
        - Token counting (estimate).
        - Cost tracking.

        Args:
            agent_type: The type of agent making the call.
            prompt: The user / task prompt.
            system_prompt: Optional system-level instructions.
            response_format: Optional Pydantic model for structured output
                             (passed as ``response_format`` to the API).
            max_retries: Maximum number of retry attempts.
            temperature: Sampling temperature (0.0 - 2.0).

        Returns:
            The model response text.

        Raises:
            RuntimeError: If all models and retries are exhausted.
        """
        route = self.get_route(agent_type)
        models_to_try = [route.primary_model]
        if route.fallback_model and route.fallback_model != route.primary_model:
            models_to_try.append(route.fallback_model)

        last_error: Exception | None = None

        for model_name in models_to_try:
            for attempt in range(1, max_retries + 1):
                try:
                    start = time.monotonic()
                    response_text = await self._do_call(
                        model_name=model_name,
                        prompt=prompt,
                        system_prompt=system_prompt,
                        response_format=response_format,
                        temperature=temperature,
                    )
                    elapsed_ms = (time.monotonic() - start) * 1000

                    # Log the successful call
                    in_tokens = _count_tokens(system_prompt or "") + _count_tokens(prompt)
                    out_tokens = _count_tokens(response_text)
                    try:
                        cost = ModelConfig.estimate_cost(
                            model_name, in_tokens, out_tokens
                        )
                    except KeyError:
                        cost = 0.0

                    self._call_log.append(
                        {
                            "timestamp": _now_iso(),
                            "agent_type": agent_type,
                            "model": model_name,
                            "attempt": attempt,
                            "success": True,
                            "latency_ms": round(elapsed_ms, 2),
                            "input_tokens": in_tokens,
                            "output_tokens": out_tokens,
                            "cost": round(cost, 6),
                        }
                    )
                    return response_text

                except Exception as exc:
                    last_error = exc
                    elapsed_ms = (time.monotonic() - start) * 1000 if "start" in dir() else 0.0

                    self._call_log.append(
                        {
                            "timestamp": _now_iso(),
                            "agent_type": agent_type,
                            "model": model_name,
                            "attempt": attempt,
                            "success": False,
                            "latency_ms": round(elapsed_ms, 2),
                            "input_tokens": 0,
                            "output_tokens": 0,
                            "cost": 0.0,
                            "error": str(exc),
                        }
                    )

                    # Don't retry if the model is fundamentally unavailable.
                    if _is_non_retryable(exc):
                        break

                    # Exponential back-off before retry
                    if attempt < max_retries:
                        await asyncio.sleep(0.5 * (2 ** (attempt - 1)))

        raise RuntimeError(
            f"All models exhausted for agent_type={agent_type!r}. "
            f"Last error: {last_error}"
        )

    # ------------------------------------------------------------------
    # Internal API call
    # ------------------------------------------------------------------

    async def _do_call(
        self,
        model_name: str,
        prompt: str,
        system_prompt: str | None = None,
        response_format: type | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Perform a single API call to the given model.

        Supports OpenAI and local (Ollama) models.
        """
        provider = self._get_provider(model_name)

        if provider == "openai":
            return await self._call_openai(
                model=model_name,
                prompt=prompt,
                system_prompt=system_prompt,
                response_format=response_format,
                temperature=temperature,
            )
        elif provider == "ollama":
            return await self._call_ollama(
                model=model_name,
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )
        else:
            raise ValueError(f"Unsupported provider {provider!r} for model {model_name!r}")

    # ------------------------------------------------------------------
    # OpenAI
    # ------------------------------------------------------------------

    async def _call_openai(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        response_format: type | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Call an OpenAI-compatible chat completion API."""
        client = self._get_openai_client()

        messages: list[dict[str, Any]] = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = await client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Ollama (local)
    # ------------------------------------------------------------------

    async def _call_ollama(
        self,
        model: str,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Call a local Ollama model via its HTTP API."""
        import httpx

        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "temperature": temperature,
            "stream": False,
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response", "")

    # ------------------------------------------------------------------
    # Provider helpers
    # ------------------------------------------------------------------

    def _get_provider(self, model_name: str) -> str:
        """Determine the provider for *model_name*.

        Falls back to ``"ollama"`` for unknown models.
        """
        try:
            cfg = ModelConfig.get(model_name)
            return cfg["provider"]
        except KeyError:
            return "ollama"

    # ------------------------------------------------------------------
    # Cost estimates
    # ------------------------------------------------------------------

    def get_cost_estimate(
        self, agent_type: str, estimated_tokens: int
    ) -> float:
        """Return an estimated cost in USD for a call of *estimated_tokens*.

        Uses the route's primary model for the calculation.
        """
        route = self.get_route(agent_type)
        try:
            cfg = ModelConfig.get(route.primary_model)
        except KeyError:
            return 0.0
        return estimated_tokens * (cfg["cost_input"] + cfg["cost_output"]) / 2

    # ------------------------------------------------------------------
    # Usage report
    # ------------------------------------------------------------------

    def get_usage_report(self) -> dict[str, Any]:
        """Return aggregate usage statistics.

        Returns:
            A dict with:
            - ``calls_by_model``: ``{model_name: count}``
            - ``total_cost``: cumulative cost in USD.
            - ``avg_latency_ms``: average latency across all calls.
            - ``total_calls``: total number of call attempts.
            - ``successful_calls``: number of successful calls.
            - ``failed_calls``: number of failed calls.
        """
        total = len(self._call_log)
        if total == 0:
            return {
                "calls_by_model": {},
                "total_cost": 0.0,
                "avg_latency_ms": 0.0,
                "total_calls": 0,
                "successful_calls": 0,
                "failed_calls": 0,
            }

        model_counter: Counter[str] = Counter()
        total_cost = 0.0
        total_latency = 0.0
        successes = 0

        for entry in self._call_log:
            model_counter[entry["model"]] += 1
            total_cost += entry["cost"]
            total_latency += entry["latency_ms"]
            if entry["success"]:
                successes += 1

        return {
            "calls_by_model": dict(model_counter),
            "total_cost": round(total_cost, 6),
            "avg_latency_ms": round(total_latency / total, 2),
            "total_calls": total,
            "successful_calls": successes,
            "failed_calls": total - successes,
        }

    def reset_usage(self) -> None:
        """Clear the in-memory usage log."""
        self._call_log.clear()


# ---------------------------------------------------------------------------
# Error classification
# ---------------------------------------------------------------------------


def _is_non_retryable(exc: Exception) -> bool:
    """Return ``True`` if retrying the same model would likely fail again."""
    msg = str(exc).lower()
    # Authentication / authorisation / not-found errors
    if any(kw in msg for kw in ("authentication", "unauthorized", "403", "401")):
        return True
    # Model not found / not supported
    if any(kw in msg for kw in ("model not found", "model_not_found", "not found")):
        return True
    # Invalid API key
    if "api key" in msg and ("invalid" in msg or "missing" in msg):
        return True
    return False
