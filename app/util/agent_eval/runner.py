# -*- coding: UTF-8 -*-
"""Agent Eval Runner — load test cases, execute agent pipeline, score results."""

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class EvalCase:
    id: str
    category: str
    input: str
    expected: dict = field(default_factory=dict)
    tags: list = field(default_factory=list)


@dataclass
class EvalResult:
    case_id: str
    category: str
    passed: bool
    score: float
    details: dict = field(default_factory=dict)
    duration_ms: float = 0.0


class EvalRunner:
    """Load and execute agent evaluation test cases.

    Usage::

        runner = EvalRunner("app/util/agent_eval/cases")
        runner.load()
        results = runner.run(agent_chat_function)
        report = runner.report()
    """

    def __init__(self, case_dir: str = None):
        if case_dir is None:
            case_dir = os.path.join(os.path.dirname(__file__), "cases")
        self.case_dir = case_dir
        self.cases: list[EvalCase] = []
        self.results: list[EvalResult] = []

    def load(self) -> int:
        """Load all case JSON files from the case directory.

        Returns number of cases loaded.
        """
        self.cases = []
        if not os.path.isdir(self.case_dir):
            logging.warning("EvalRunner: case dir not found: %s", self.case_dir)
            return 0

        for fname in sorted(os.listdir(self.case_dir)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(self.case_dir, fname)
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, IOError) as ex:
                logging.warning("EvalRunner: failed to load %s: %s", fname, ex)
                continue

            cases_data = data if isinstance(data, list) else [data]
            for c in cases_data:
                self.cases.append(EvalCase(
                    id=c.get("id", f"{fname}:{len(self.cases)}"),
                    category=c.get("category", "general"),
                    input=c.get("input", ""),
                    expected=c.get("expected", {}),
                    tags=c.get("tags", []),
                ))

        logging.info("EvalRunner: loaded %d cases from %d files", len(self.cases),
                      len(os.listdir(self.case_dir)))
        return len(self.cases)

    def run(self, agent_fn: Callable, *, verbose: bool = False) -> list[EvalResult]:
        """Execute all loaded test cases against the agent function.

        Args:
            agent_fn: Callable(user_message) → dict with keys:
                {"route": str, "text": str, "tool_calls": list, "duration_ms": float}
            verbose: If True, log per-case results.

        Returns:
            List of EvalResult objects.
        """
        self.results = []
        for case in self.cases:
            t0 = time.time()
            try:
                output = agent_fn(case.input)
            except Exception as ex:
                logging.warning("EvalRunner: case %s error: %s", case.id, ex)
                output = {"route": "error", "text": str(ex), "tool_calls": [], "duration_ms": 0}

            duration = (time.time() - t0) * 1000
            score, details = self._score(case, output)
            result = EvalResult(
                case_id=case.id, category=case.category,
                passed=score >= 0.5,
                score=score,
                details=details,
                duration_ms=duration,
            )
            self.results.append(result)

            if verbose:
                mark = "PASS" if result.passed else "FAIL"
                logging.info("EvalRunner: [%s] %s — %s (score=%.2f)", mark, case.id, case.input[:50], score)

        return self.results

    def report(self) -> dict:
        """Generate evaluation summary report.

        Returns:
            {"total": int, "passed": int, "failed": int, "pass_rate": float,
             "by_category": {cat: {"total": N, "passed": N, "rate": f}}, "avg_score": float}
        """
        if not self.results:
            return {"total": 0, "passed": 0, "failed": 0, "pass_rate": 0.0,
                    "by_category": {}, "avg_score": 0.0}

        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        failed = total - passed

        by_cat = {}
        for r in self.results:
            if r.category not in by_cat:
                by_cat[r.category] = {"total": 0, "passed": 0}
            by_cat[r.category]["total"] += 1
            if r.passed:
                by_cat[r.category]["passed"] += 1

        for cat, stats in by_cat.items():
            stats["rate"] = round(stats["passed"] / max(stats["total"], 1), 3)

        avg_score = sum(r.score for r in self.results) / max(total, 1)

        return {
            "total": total, "passed": passed, "failed": failed,
            "pass_rate": round(passed / max(total, 1), 3),
            "by_category": by_cat,
            "avg_score": round(avg_score, 3),
        }

    def print_report(self):
        """Log a human-readable evaluation report."""
        r = self.report()
        logging.info(f"\n{'='*50}")
        logging.info(f"  Agent Eval Report")
        logging.info(f"{'='*50}")
        logging.info(f"  Total:  {r['total']}")
        logging.info(f"  Passed: {r['passed']}")
        logging.info(f"  Failed: {r['failed']}")
        logging.info(f"  Rate:   {r['pass_rate']:.1%}")
        logging.info(f"  Avg:    {r['avg_score']:.2f}")
        logging.info(f"{'─'*50}")
        if r["by_category"]:
            logging.info(f"  By Category:")
            for cat, stats in sorted(r["by_category"].items()):
                logging.info(f"    {cat:12s}: {stats['passed']}/{stats['total']} ({stats['rate']:.0%})")
        logging.info(f"{'='*50}\n")

    # ── Scoring ────────────────────────────────────────────────────────

    @staticmethod
    def _score(case: EvalCase, output: dict) -> tuple[float, dict]:
        """Score a single test case against expected criteria.

        Returns (score 0.0~1.0, details dict).
        """
        expected = case.expected
        if not expected:
            return 1.0, {"reason": "no criteria"}

        checks = []
        details = {}

        # 1. Route accuracy
        if "route" in expected:
            actual_route = output.get("route", "")
            ok = actual_route == expected["route"]
            checks.append(1.0 if ok else 0.0)
            details["route"] = {"expected": expected["route"], "actual": actual_route, "ok": ok}

        # 2. Tool call presence
        if "has_tool_calls" in expected:
            actual_tools = output.get("tool_calls", [])
            has = len(actual_tools) > 0
            ok = has == expected["has_tool_calls"]
            checks.append(1.0 if ok else 0.0)
            details["has_tool_calls"] = {"expected": expected["has_tool_calls"], "actual": has, "ok": ok}

        # 3. String contains
        text = output.get("text", "")
        if "contains" in expected:
            for keyword in expected["contains"]:
                ok = keyword.lower() in text.lower()
                checks.append(1.0 if ok else 0.0)
                details[f"contains:{keyword}"] = {"ok": ok}

        # 4. String NOT contains
        if "not_contains" in expected:
            for keyword in expected["not_contains"]:
                ok = keyword.lower() not in text.lower()
                checks.append(1.0 if ok else 0.0)
                details[f"not_contains:{keyword}"] = {"ok": ok}

        # 5. Tool names
        if "tool_names" in expected:
            actual_names = [tc.get("name", tc.get("function", {}).get("name", ""))
                           for tc in output.get("tool_calls", [])]
            for tname in expected["tool_names"]:
                ok = tname in actual_names
                checks.append(1.0 if ok else 0.0)
                details[f"tool:{tname}"] = {"expected": True, "actual": ok, "ok": ok}

        if not checks:
            return 1.0, {"reason": "no checkable criteria"}

        score = sum(checks) / len(checks)
        details["_score"] = round(score, 3)
        details["_checks"] = len(checks)
        return score, details
