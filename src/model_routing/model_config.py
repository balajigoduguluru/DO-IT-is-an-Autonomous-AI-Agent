"""Configuration catalogue for all available LLM models."""

from __future__ import annotations

from typing import Any


class ModelConfig:
    """Static catalogue of model metadata.

    Each entry contains:
    - ``provider``: ``"openai"``, ``"ollama"``, etc.
    - ``context``: maximum context window in tokens.
    - ``cost_input``: cost per input token (USD).
    - ``cost_output``: cost per output token (USD).
    """

    MODELS: dict[str, dict[str, Any]] = {
        "gpt-4o": {
            "provider": "openai",
            "context": 128000,
            "cost_input": 2.5 / 1e6,
            "cost_output": 10.0 / 1e6,
        },
        "gpt-4o-mini": {
            "provider": "openai",
            "context": 128000,
            "cost_input": 0.15 / 1e6,
            "cost_output": 0.6 / 1e6,
        },
        "gpt-5.5": {
            "provider": "openai",
            "context": 256000,
            "cost_input": 10.0 / 1e6,
            "cost_output": 40.0 / 1e6,
        },
        "gpt-5.5-mini": {
            "provider": "openai",
            "context": 128000,
            "cost_input": 0.4 / 1e6,
            "cost_output": 1.6 / 1e6,
        },
        "qwen3": {
            "provider": "ollama",
            "context": 32000,
            "cost_input": 0.0,
            "cost_output": 0.0,
        },
        "local": {
            "provider": "ollama",
            "context": 8192,
            "cost_input": 0.0,
            "cost_output": 0.0,
        },
    }

    @classmethod
    def get(cls, model_name: str) -> dict[str, Any]:
        """Return the configuration dict for *model_name*.

        Args:
            model_name: The model identifier (e.g. ``"gpt-4o"``).

        Returns:
            The configuration dict.

        Raises:
            KeyError: If the model is not in the catalogue.
        """
        model = cls.MODELS.get(model_name)
        if model is None:
            raise KeyError(
                f"Unknown model {model_name!r}. "
                f"Available: {', '.join(sorted(cls.MODELS))}"
            )
        return dict(model)

    @classmethod
    def is_available(cls, model_name: str) -> bool:
        """Check whether *model_name* is present in the catalogue.

        This checks only the configuration registry, not runtime
        availability of the provider API.
        """
        return model_name in cls.MODELS

    @classmethod
    def get_cheapest_available(
        cls, min_context: int = 0
    ) -> str:
        """Return the name of the cheapest model with at least *min_context* tokens.

        Models with zero cost (local / Ollama) are preferred, otherwise the
        one with the lowest ``cost_input + cost_output`` is selected.

        Args:
            min_context: Minimum required context window size.

        Returns:
            Model name string.

        Raises:
            ValueError: If no model meets the context requirement.
        """
        candidates: list[tuple[str, dict[str, Any]]] = [
            (name, cfg)
            for name, cfg in cls.MODELS.items()
            if cfg["context"] >= min_context
        ]
        if not candidates:
            raise ValueError(
                f"No model available with context >= {min_context}"
            )

        # Sort: zero-cost first, then by total cost (input + output).
        def _sort_key(item: tuple[str, dict[str, Any]]) -> tuple[float, float]:
            _name, cfg = item
            total_cost = cfg["cost_input"] + cfg["cost_output"]
            return (total_cost, cfg["context"])

        candidates.sort(key=_sort_key)
        return candidates[0][0]

    @classmethod
    def estimate_cost(
        cls, model_name: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimate the cost of a call to *model_name*.

        Args:
            model_name: The model identifier.
            input_tokens: Number of input (prompt) tokens.
            output_tokens: Number of output (completion) tokens.

        Returns:
            Estimated cost in USD.
        """
        cfg = cls.get(model_name)
        return (
            input_tokens * cfg["cost_input"]
            + output_tokens * cfg["cost_output"]
        )

    @classmethod
    def register(cls, model_name: str, config: dict[str, Any]) -> None:
        """Add or override a model entry in the catalogue.

        Args:
            model_name: The model identifier.
            config: Dict with keys ``provider``, ``context``,
                    ``cost_input``, ``cost_output``.
        """
        required_keys = {"provider", "context", "cost_input", "cost_output"}
        missing = required_keys - set(config)
        if missing:
            raise ValueError(
                f"Missing required config keys for {model_name!r}: {missing}"
            )
        cls.MODELS[model_name] = {
            "provider": str(config["provider"]),
            "context": int(config["context"]),
            "cost_input": float(config["cost_input"]),
            "cost_output": float(config["cost_output"]),
        }
