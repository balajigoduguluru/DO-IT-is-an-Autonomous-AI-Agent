"""Worker agent — universal executor that routes to any registered tool.

The Worker is the only agent that invokes external tools (APIs, databases,
LLM inference endpoints, etc.).  It:

1. Resolves the tool via a :class:`ToolRegistry`.
2. Runs risk assessment before executing.
3. Executes the tool (with fallback if the primary tool fails).
4. Returns the result with metadata.

No specialised agent per tool type — this single class handles everything.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from src.core.constants import RiskLevel
from src.core.models import (
    RiskAssessment,
    TaskNode,
    ToolCallResult,
    ToolRegistration,
)


@runtime_checkable
class ModelRouter(Protocol):
    """Callable that routes a prompt to an LLM and returns the response.

    Used by the Worker for risk assessment.  The caller (typically the
    main orchestration loop) provides this so the Worker can request
    LLM-based analysis without owning an LLM client itself.
    """

    async def __call__(self, prompt: str, **kwargs: Any) -> Any:
        ...


# ===========================================================================
# Tool Registry
# ===========================================================================


class ToolRegistry:
    """Registry mapping tool names to metadata and optional async handlers.

    Handlers are async callables that accept the input dict and return
    the result data.  When no handler is registered, the Worker will
    attempt to call the tool by name — implementations that require
    custom logic should inject a handler.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolRegistration] = {}
        self._handlers: dict[str, Callable[..., Awaitable[Any]]] = {}

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        registration: ToolRegistration,
        handler: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        """Register a tool.

        Args:
            registration: Tool metadata.
            handler: Optional async callable that implements the tool.
        """
        self._tools[registration.name] = registration
        if handler is not None:
            self._handlers[registration.name] = handler

    def unregister(self, name: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(name, None)
        self._handlers.pop(name, None)

    # ------------------------------------------------------------------
    # Lookup
    # ------------------------------------------------------------------

    def get(self, name: str) -> ToolRegistration | None:
        """Look up tool metadata by name."""
        return self._tools.get(name)

    def get_handler(self, name: str) -> Callable[..., Awaitable[Any]] | None:
        """Return the registered handler for *name*, or ``None``."""
        return self._handlers.get(name)

    def list_tools(self) -> list[ToolRegistration]:
        """List all registered tools."""
        return list(self._tools.values())

    # ------------------------------------------------------------------
    # Fallback
    # ------------------------------------------------------------------

    def resolve_fallback_chain(self, tool_name: str) -> list[str]:
        """Build an ordered fallback chain starting with *tool_name*.

        The chain includes *tool_name* first, followed by any alternatives
        in :attr:`ToolRegistration.fallback_chain`.
        """
        reg = self.get(tool_name)
        if reg is None:
            return [tool_name]
        return [tool_name] + list(reg.fallback_chain)

    # ------------------------------------------------------------------
    # Container protocol
    # ------------------------------------------------------------------

    def __contains__(self, name: str) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)


# ===========================================================================
# Worker Agent
# ===========================================================================


class WorkerAgent:
    """Universal executor that routes tasks to registered tools.

    The worker owns no state — it receives a task description and a
    :class:`ToolRegistry`, executes the appropriate tool (with fallback
    and risk assessment), and returns the result.

    Attributes:
        tool_registry: Registry of available tools and their handlers.
    """

    def __init__(self, tool_registry: ToolRegistry) -> None:
        """Configure the worker.

        Args:
            tool_registry: A populated :class:`ToolRegistry` instance.
        """
        self.tool_registry = tool_registry

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute_task(
        self,
        task: TaskNode,
        model_router: ModelRouter | None = None,
    ) -> dict[str, Any]:
        """Execute a single :class:`TaskNode`.

        Steps:

        1. Resolve which tool to use via the :attr:`tool_registry`.
        2. Run risk assessment before execution (optionally using the
           *model_router* for high-risk tools).
        3. Execute the tool (with fallback on failure).
        4. Return a result dict with success/failure, data/error, timing
           metadata, and risk assessment.

        Args:
            task: The task node to execute.
            model_router: Optional LLM callable for risk assessment of
                high-risk operations.

        Returns:
            A dict with keys ``task_id``, ``success``, ``data``,
            ``error``, ``execution_time_ms``, ``risk_assessment``, and
            ``metadata``.
        """
        tool_name = task.input.get("tool", "")
        params = task.input.get("params", task.input)

        # ---- Step 1: Resolve tool -----------------------------------------
        registration = self.tool_registry.get(tool_name)
        if registration is None:
            return {
                "task_id": task.id,
                "success": False,
                "error": f"Tool '{tool_name}' is not registered",
                "data": None,
                "execution_time_ms": 0,
                "risk_assessment": RiskAssessment(
                    risk_level=RiskLevel.HIGH,
                    reasoning=f"Unknown tool '{tool_name}' — rejected before execution",
                ),
                "metadata": {},
            }

        # ---- Step 2: Risk assessment --------------------------------------
        risk_result = await self._assess_risk(registration, params, model_router)

        if risk_result.risk_level == RiskLevel.CRITICAL:
            return {
                "task_id": task.id,
                "success": False,
                "error": f"Critical risk: {risk_result.reasoning}",
                "data": None,
                "execution_time_ms": 0,
                "risk_assessment": risk_result,
                "metadata": {},
            }

        # ---- Step 3 & 4: Execute with fallback ----------------------------
        result = await self.execute_with_fallback(
            tool_name, params, risk_result
        )

        # ---- Step 5: Compose result dict ----------------------------------
        return {
            "task_id": task.id,
            "success": result.success,
            "data": result.output if result.success else None,
            "error": result.error,
            "execution_time_ms": result.latency_ms,
            "risk_assessment": risk_result,
            "metadata": {
                "tool_used": result.tool_name,
                **result.model_dump(exclude={"tool_name", "success", "output", "error", "latency_ms", "cost"}),
            },
        }

    async def execute_with_fallback(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        risk_result: RiskAssessment,  # noqa: ARG002 (available for logging)
    ) -> ToolCallResult:
        """Execute *tool_name* with fallback on failure.

        Walks the :attr:`tool_registry` fallback chain.  Each attempt
        calls the tool's registered handler (or delegates to
        :meth:`_call_tool` if no handler exists).

        Args:
            tool_name: The primary tool to attempt.
            input_data: Parameters to pass to the tool.
            risk_result: Preliminary risk assessment (logged, but does
                not affect execution flow here).

        Returns:
            A :class:`ToolCallResult` with the first successful result or
            the last failure.
        """
        chain = self.tool_registry.resolve_fallback_chain(tool_name)
        last_error: str | None = None

        for attempt_name in chain:
            registration = self.tool_registry.get(attempt_name)
            if registration is None:
                last_error = f"Tool '{attempt_name}' not found in registry"
                continue

            start = time.perf_counter()
            try:
                output = await self._call_tool(registration, input_data)
                elapsed_ms = int((time.perf_counter() - start) * 1000)

                return ToolCallResult(
                    tool_name=attempt_name,
                    success=True,
                    output=output,
                    latency_ms=elapsed_ms,
                )

            except Exception as exc:
                elapsed_ms = int((time.perf_counter() - start) * 1000)
                last_error = str(exc)

                # If this was the last item in the chain, return the failure.
                if attempt_name == chain[-1]:
                    return ToolCallResult(
                        tool_name=attempt_name,
                        success=False,
                        error=last_error,
                        latency_ms=elapsed_ms,
                    )

        return ToolCallResult(
            tool_name=tool_name,
            success=False,
            error=last_error or "Fallback chain exhausted",
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _assess_risk(
        self,
        registration: ToolRegistration,
        input_data: dict[str, Any],
        model_router: ModelRouter | None,
    ) -> RiskAssessment:
        """Assess the risk of executing *registration* with *input_data*.

        For low- and medium-risk tools, returns the preset risk level
        from the registration.  For higher-risk tools, optionally consults
        the *model_router* for a detailed assessment.

        Args:
            registration: The tool's metadata.
            input_data: Parameters being passed to the tool.
            model_router: Optional LLM callable for dynamic assessment.

        Returns:
            A :class:`RiskAssessment` instance.
        """
        # Map the tool's risk level to our RiskLevel enum.
        # ToolRegistration doesn't have a direct risk field, so we use
        # a heuristic based on tool category.
        base_risk = self._category_risk(registration.category)

        if base_risk in (RiskLevel.LOW, RiskLevel.MEDIUM):
            return RiskAssessment(
                risk_level=base_risk,
                confidence=0.8,
                reasoning=f"Preset risk for category '{registration.category.value}': {base_risk.value}",
            )

        # HIGH or CRITICAL — consult LLM if available
        if model_router is not None:
            try:
                prompt = (
                    f"Assess the risk of executing tool '{registration.name}' "
                    f"(category: {registration.category.value}) "
                    f"with input: {input_data}. "
                    f"Return JSON with 'risk_level' (LOW/MEDIUM/HIGH/CRITICAL), "
                    f"'reasoning', and 'suggested_mitigation' (or null)."
                )
                resp = await model_router(prompt)
                if isinstance(resp, dict):
                    return RiskAssessment(
                        risk_level=RiskLevel(
                            resp.get("risk_level", base_risk.value)
                        ),
                        reasoning=resp.get("reasoning", ""),
                        security_flags=[],
                        cost_estimate=0.0,
                        confidence=0.7,
                        failure_probability=0.0,
                        requires_approval=resp.get("risk_level", "LOW") in ("HIGH", "CRITICAL"),
                    )
            except Exception:
                pass

        return RiskAssessment(
            risk_level=base_risk,
            reasoning=f"Risk assessment via LLM unavailable; using category default ({base_risk.value})",
        )

    async def _call_tool(
        self,
        registration: ToolRegistration,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Actually invoke the tool and return its output.

        If a handler is registered for this tool, it is called.
        Otherwise a :class:`NotImplementedError` is raised — subclasses
        or callers should register handlers for all tools they intend
        to use.

        Args:
            registration: The tool metadata (includes the name).
            input_data: Parameters to pass to the handler.

        Returns:
            The tool's output as a dict (must be JSON-serialisable).
        """
        handler = self.tool_registry.get_handler(registration.name)
        if handler is None:
            raise NotImplementedError(
                f"No handler registered for tool '{registration.name}'. "
                "Register a handler via ToolRegistry.register()."
            )
        result = await handler(**input_data)
        if isinstance(result, dict):
            return result
        return {"result": result}

    @staticmethod
    def _category_risk(category: Any) -> RiskLevel:
        """Heuristic risk level based on tool category."""
        from src.core.constants import ToolCategory

        high_risk = {ToolCategory.EMAIL, ToolCategory.GENERAL}
        medium_risk = {ToolCategory.FLIGHT, ToolCategory.HOTEL, ToolCategory.TRANSPORT}
        low_risk = {ToolCategory.WEATHER, ToolCategory.BUDGET, ToolCategory.SEARCH}

        if category in high_risk:
            return RiskLevel.HIGH
        if category in medium_risk:
            return RiskLevel.MEDIUM
        if category in low_risk:
            return RiskLevel.LOW
        return RiskLevel.MEDIUM
