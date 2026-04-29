"""
Stage A – Deterministic Recovery Planner.

Builds a dependency-aware, topologically-sorted recovery ordering from
`data/dependencies.json` and the list of impacted services reported in the
incident.

Algorithm:
1. Load the dependency graph from JSON.
2. Expand the seed impacted services to include all transitive hard dependencies.
3. Topologically sort using Kahn's algorithm (tier-based for ties).
4. Return an ordered list of service IDs with per-step metadata.
"""

from __future__ import annotations

import json
import logging
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal data structures
# ---------------------------------------------------------------------------


class ServiceNode:
    """Represents one node in the PilotFish dependency graph."""

    def __init__(self, data: dict[str, Any]) -> None:
        self.id: str = data["id"]
        self.display_name: str = data.get("display_name", self.id)
        self.description: str = data.get("description", "")
        self.tier: int = data.get("tier", 99)
        self.depends_on: list[dict[str, str]] = data.get("depends_on", [])
        self.recovery_prereqs: list[str] = data.get("recovery_prereqs", [])
        self.recovery_actions: list[str] = data.get("recovery_actions", [])
        self.health_signals: list[dict[str, str]] = data.get("health_signals", [])


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class RecoveryPlanner:
    """
    Deterministic planner that converts an incident's impacted services into
    an ordered recovery sequence respecting hard dependencies.
    """

    def __init__(self, dependencies_path: str | Path) -> None:
        self._path = Path(dependencies_path)
        self._graph: dict[str, ServiceNode] = {}
        self._load_graph()

    # ------------------------------------------------------------------
    # Graph loading
    # ------------------------------------------------------------------

    def _load_graph(self) -> None:
        if not self._path.exists():
            logger.warning("dependencies.json not found at %s – using empty graph", self._path)
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for svc in raw.get("services", []):
            node = ServiceNode(svc)
            self._graph[node.id] = node
        logger.info("Loaded %d services from dependency graph", len(self._graph))

    # ------------------------------------------------------------------
    # Core planning
    # ------------------------------------------------------------------

    def plan(self, impacted_services: list[str], incident_description: str = "") -> list[dict]:
        """
        Return an ordered list of recovery step dicts for the given impacted services.

        Each dict contains:
            service_id, display_name, tier, why_now, recovery_actions,
            recovery_prereqs, is_gated, hard_deps
        """
        # Expand to all hard dependencies transitively
        all_services = self._expand_dependencies(set(impacted_services))

        # Infer services from description keywords if not explicitly listed
        if not all_services:
            all_services = self._infer_services_from_text(incident_description)
            all_services = self._expand_dependencies(all_services)

        if not all_services:
            logger.warning("No services identified; returning empty plan")
            return []

        ordered = self._topological_sort(all_services)
        return self._build_steps(ordered, set(impacted_services))

    def _expand_dependencies(self, seed: set[str]) -> set[str]:
        """BFS expansion of hard dependencies."""
        visited: set[str] = set()
        queue = deque(seed)
        while queue:
            svc_id = queue.popleft()
            if svc_id in visited:
                continue
            visited.add(svc_id)
            node = self._graph.get(svc_id)
            if not node:
                continue
            for dep in node.depends_on:
                if dep.get("type") == "hard" and dep["service"] not in visited:
                    queue.append(dep["service"])
        return visited

    def _infer_services_from_text(self, text: str) -> set[str]:
        """Keyword match service IDs from free-text incident description."""
        text_lower = text.lower()
        matched: set[str] = set()
        for svc_id, node in self._graph.items():
            keywords = [svc_id.lower(), node.display_name.lower()]
            # also match simple name fragments
            parts = svc_id.lower().split(".")
            keywords.extend(parts)
            if any(kw in text_lower for kw in keywords if len(kw) > 3):
                matched.add(svc_id)
        return matched

    def _topological_sort(self, service_ids: set[str]) -> list[str]:
        """
        Kahn's algorithm over the subgraph of `service_ids`.
        Hard deps must come before dependents; tier used as tiebreaker.
        """
        # Build in-degree map restricted to selected services
        in_degree: dict[str, int] = {s: 0 for s in service_ids}
        adjacency: dict[str, list[str]] = {s: [] for s in service_ids}

        for svc_id in service_ids:
            node = self._graph.get(svc_id)
            if not node:
                continue
            for dep in node.depends_on:
                dep_svc = dep["service"]
                if dep_svc in service_ids:
                    in_degree[svc_id] += 1
                    adjacency[dep_svc].append(svc_id)

        # Use a priority queue (min-heap on tier) to keep ordering deterministic
        import heapq

        ready: list[tuple[int, str]] = []
        for svc_id, deg in in_degree.items():
            if deg == 0:
                tier = self._graph[svc_id].tier if svc_id in self._graph else 99
                heapq.heappush(ready, (tier, svc_id))

        result: list[str] = []
        while ready:
            _, svc_id = heapq.heappop(ready)
            result.append(svc_id)
            for neighbor in adjacency.get(svc_id, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    tier = self._graph[neighbor].tier if neighbor in self._graph else 99
                    heapq.heappush(ready, (tier, neighbor))

        # Append any remaining (cycle fallback) in tier order
        remaining = [s for s in service_ids if s not in result]
        remaining.sort(key=lambda s: self._graph[s].tier if s in self._graph else 99)
        result.extend(remaining)

        return result

    def _build_steps(self, ordered: list[str], originally_impacted: set[str]) -> list[dict]:
        steps = []
        for idx, svc_id in enumerate(ordered, start=1):
            node = self._graph.get(svc_id)
            hard_deps = []
            if node:
                hard_deps = [
                    d["service"] for d in node.depends_on if d.get("type") == "hard"
                ]

            why_now = self._explain_ordering(svc_id, idx, hard_deps, ordered)

            steps.append(
                {
                    "step_number": idx,
                    "service_id": svc_id,
                    "display_name": node.display_name if node else svc_id,
                    "tier": node.tier if node else 99,
                    "why_now": why_now,
                    "recovery_actions": node.recovery_actions if node else [],
                    "recovery_prereqs": node.recovery_prereqs if node else [],
                    "hard_deps": hard_deps,
                    "is_gated": bool(hard_deps),
                    "is_direct_impact": svc_id in originally_impacted,
                }
            )
        return steps

    @staticmethod
    def _explain_ordering(
        svc_id: str, position: int, hard_deps: list[str], ordered: list[str]
    ) -> str:
        if not hard_deps:
            return (
                f"{svc_id} has no hard dependencies; recover as the first priority at step {position}."
            )
        dep_positions = [ordered.index(d) + 1 for d in hard_deps if d in ordered]
        if dep_positions:
            dep_str = ", ".join(hard_deps)
            pos_str = ", ".join(str(p) for p in dep_positions)
            return (
                f"Recover after hard dependencies [{dep_str}] (steps {pos_str}). "
                f"Starting {svc_id} before them will cause initialization failures."
            )
        return f"Recover {svc_id} at step {position}."
