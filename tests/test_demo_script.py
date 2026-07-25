"""Tests for the demo script.

Verifies that the DemoRunner initializes correctly and produces the
expected output steps.
"""

import asyncio
import sys
from pathlib import Path

import pytest

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from scripts.demo import DemoRunner


class TestDemoScript:
    """Test that the demo script runs without errors and produces correct
    output.
    """

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_demo_runner_init(self) -> None:
        """Test DemoRunner initialization."""
        runner = DemoRunner()
        assert runner.use_real_llm is False
        assert runner.start_time is None
        assert runner.steps == []

        runner = DemoRunner(use_real_llm=True)
        assert runner.use_real_llm is True

    @pytest.mark.asyncio
    async def test_demo_runner_init_default(self) -> None:
        """Test DemoRunner default parameters."""
        runner = DemoRunner()
        assert runner.use_real_llm is False

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_demo_log_basic(self) -> None:
        """Test basic logging stores steps correctly."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log("Test step", "Test detail")
        assert len(runner.steps) == 1
        entry = runner.steps[0]
        assert entry["step"] == "Test step"
        assert entry["detail"] == "Test detail"

    @pytest.mark.asyncio
    async def test_demo_log_ok(self) -> None:
        """Test log_ok stores correct step."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log_ok("Success step", "Everything worked")
        assert len(runner.steps) == 1
        entry = runner.steps[0]
        assert "Success step" in entry["step"]
        assert entry["detail"] == "Everything worked"

    @pytest.mark.asyncio
    async def test_demo_log_fail(self) -> None:
        """Test log_fail stores correct step."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log_fail("Failed step", "Something broke")
        assert len(runner.steps) == 1
        entry = runner.steps[0]
        assert "Failed step" in entry["step"]
        assert entry["detail"] == "Something broke"

    @pytest.mark.asyncio
    async def test_demo_log_warn(self) -> None:
        """Test log_warn stores correct step."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log_warn("Warning step", "Proceed with caution")
        assert len(runner.steps) == 1

    @pytest.mark.asyncio
    async def test_demo_log_info(self) -> None:
        """Test log_info stores correct step."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log_info("Info step", "Some information")
        assert len(runner.steps) == 1

    @pytest.mark.asyncio
    async def test_demo_log_action(self) -> None:
        """Test log_action stores correct step."""
        runner = DemoRunner()
        runner.start_time = 0.0

        runner.log_action("Action step", "Doing something")
        assert len(runner.steps) == 1

    @pytest.mark.asyncio
    async def test_logging_no_start_time(self) -> None:
        """Test logging without start_time set."""
        runner = DemoRunner()
        runner.log("Step without start", "Detail")
        assert len(runner.steps) == 1
        # Time should be 0.0 since start_time is None
        entry = runner.steps[0]
        assert entry["time"] == 0.0

    # ------------------------------------------------------------------
    # Demo output structure
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_demo_output_steps(self) -> None:
        """Test that demo produces expected output steps."""
        runner = DemoRunner()
        runner.start_time = 0.0

        # Simulate all the demo steps
        runner.log_info("User goal received", "Plan Bangalore trip")
        runner.log_action("Supervisor analysing goal", "")
        runner.log_ok("Destination extracted", "Bangalore")
        runner.log_ok("Budget parsed", "₹30,000")
        runner.log_action("Planner building DAG", "")
        runner.log_ok("DAG built", "6 tasks, 3 parallel groups")
        runner.log_action("Executing Group 0", "3 tasks in parallel")
        runner.log_ok("Weather check completed", "26°C")
        runner.log_ok("Hotel search completed", "3 options found")
        runner.log_fail("Flight API Error", "503 Service Unavailable")
        runner.log_action("Risk Predictor analysing failure", "")
        runner.log_ok("Risk assessment complete", "High failure risk")
        runner.log_action("Tool Marketplace searching alternatives", "")
        runner.log_ok("Marketplace selected train_search", "Score: 0.92")
        runner.log_action("AdaptiveExecutionGraph mutating", "")
        runner.log_ok("Graph mutated successfully", "flight → train")
        runner.log_action("Budget calculator recalculating", "")
        runner.log_ok("Budget recalculated", "Under budget by ₹15,500")
        runner.log_action("Evaluator scoring results", "")
        runner.log_ok("Evaluation passed", "Score: 92%")
        runner.log_action("Approval Gate blocking execution", "")
        runner.log_info("Approval received", "User approved")
        runner.log_ok("Approval Gate passed", "Resumed execution")
        runner.log_action("Sending summary email", "")
        runner.log_ok("Email sent", "Delivered")
        runner.log_action("Execution Ledger displaying", "")
        runner.log_action("Learning Memory storing patterns", "")
        runner.log_ok("Learning Memory updated", "4 collections updated")
        runner.log_action("Model Router cost analysis", "")
        runner.log_ok("Model routing complete", "87% savings")

        # Verify the number of steps
        assert len(runner.steps) == 30

        # Verify specific steps exist (strip ANSI codes for comparison)
        import re
        strip_ansi = lambda s: re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)
        plain_steps = [strip_ansi(s["step"]) for s in runner.steps]
        assert "User goal received" in " ".join(plain_steps)
        assert "Flight API Error" in " ".join(plain_steps)
        assert "Graph mutated successfully" in " ".join(plain_steps)
        assert "Evaluation passed" in " ".join(plain_steps)
        assert "Approval received" in " ".join(plain_steps)
        assert "Email sent" in " ".join(plain_steps)

    @pytest.mark.asyncio
    async def test_demo_timing(self) -> None:
        """Test that timing is recorded correctly in steps."""
        import time

        runner = DemoRunner()
        runner.start_time = time.time()

        await asyncio.sleep(0.01)
        runner.log("Step after delay", "Delayed detail")

        entry = runner.steps[0]
        assert entry["time"] > 0

    # ------------------------------------------------------------------
    # Full demo run (sanity check — just runs through without error)
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_demo_full_run_sanity(self) -> None:
        """Test that the full demo runs without crashing (quick mode)."""
        runner = DemoRunner()

        # Monkey-patch the progress delays to be very small
        original_progress = runner._progress

        async def fast_progress(label: str, seconds: float, colour: str = "") -> None:
            await asyncio.sleep(0.001)  # 1 ms instead of real delay

        runner._progress = fast_progress  # type: ignore[method-assign]

        # Run the full demo
        await runner.run_full_demo()

        # Should have produced many steps
        assert len(runner.steps) > 20

        # Verify key innovation-related steps exist
        all_text = " ".join(s["step"] for s in runner.steps) + " ".join(
            s["detail"] for s in runner.steps
        )
        assert "User" in all_text
        assert "DAG" in all_text
        assert "Flight" in all_text
        assert "Marketplace" in all_text
        assert "Graph" in all_text
        assert "Budget" in all_text
        assert "Evaluator" in all_text
        assert "Approval" in all_text
        assert "Ledger" in all_text
        assert "Learning" in all_text
        assert "Model" in all_text

    # ------------------------------------------------------------------
    # Progress bar helper
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_progress_bar_displays(self) -> None:
        """Test that the progress bar runs without error."""
        runner = DemoRunner()
        runner.start_time = 0.0

        await runner._progress("Testing", 0.001, "green")

