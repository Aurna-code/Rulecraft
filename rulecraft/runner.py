"""Rulecraft orchestration loop."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from pathlib import Path

from rulecraft.adapters import LLMAdapter, VerifierAdapter
from rulecraft.memory import MemoryStore
from rulecraft.policy import BudgetRouter
from rulecraft.schemas import EventLog, VerifierResult, pass_definition
from rulecraft.selector import CandidateSelector
from rulecraft.serializer import serialize_eventlog


@dataclass
class RunResult:
    output: str | dict
    verifier: VerifierResult
    event_log: EventLog


class RulecraftRunner:
    def __init__(
        self,
        *,
        llm_adapter: LLMAdapter,
        verifier: VerifierAdapter,
        memory_store: MemoryStore | None = None,
        budget_router: BudgetRouter | None = None,
        selector: CandidateSelector | None = None,
        eventlog_path: Path | None = None,
        max_attempts: int = 3,
    ) -> None:
        self.llm_adapter = llm_adapter
        self.verifier = verifier
        self.memory_store = memory_store or MemoryStore()
        self.budget_router = budget_router or BudgetRouter()
        self.selector = selector or CandidateSelector()
        self.eventlog_path = eventlog_path or Path("data") / "eventlog.jsonl"
        self.max_attempts = max_attempts

    def _build_keys(self, context: dict) -> tuple[str | None, str | None]:
        intent_key = context.get("intent_key")
        state_key = context.get("state_key")
        return intent_key, state_key

    def _build_messages(
        self, prompt: str, memory_hints: list[str]
    ) -> list[dict]:
        if memory_hints:
            injected = "\n".join(f"- {hint}" for hint in memory_hints)
            system_content = (
                "You are Rulecraft. Apply the following memory hints if relevant:\n"
                f"{injected}"
            )
            return [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ]
        return [{"role": "user", "content": prompt}]

    def _append_eventlog(self, payload: dict) -> None:
        self.eventlog_path.parent.mkdir(parents=True, exist_ok=True)
        with self.eventlog_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def run(
        self,
        *,
        prompt: str,
        context: dict,
        constraints: dict | None = None,
    ) -> RunResult:
        trace_id = context.get("trace_id") or str(uuid.uuid4())
        bucket_key = context.get("bucket_key", "I1|general|clarity_high")
        intent_key, state_key = self._build_keys(context)

        memory_response = self.memory_store.recall(
            bucket_key=bucket_key,
            intent_key=intent_key,
            state_key=state_key,
            top_k=context.get("rule_top_k", 3),
        )
        memory_hints = [item.summary for item in memory_response.items]
        selected_rules = self.selector.select(context, memory_response)

        run_mode = context.get("run_mode", "main")
        attempt = 0
        output: str | dict
        verifier = None
        while attempt < self.max_attempts:
            messages = self._build_messages(prompt, memory_hints)
            output, meta = self.llm_adapter.generate(
                messages,
                temperature=context.get("temperature", 0.2),
                max_tokens=context.get("max_tokens"),
            )

            verifier_dict = self.verifier.verify(
                trace_id=trace_id,
                x_ref=prompt,
                candidate=output,
                context={**context, "run_mode": run_mode},
                constraints=constraints,
                meta=meta,
            )
            verifier = VerifierResult(**verifier_dict)

            next_mode = self.budget_router.decide_next_mode(verifier, run_mode, attempt)
            if not next_mode:
                break
            run_mode = next_mode
            attempt += 1

        event_log = EventLog(
            schema_version=verifier.schema_version,
            trace_id=trace_id,
            bucket_key=bucket_key,
            intent_key=intent_key,
            state_key=state_key,
            x_ref=prompt,
            run_mode=run_mode,
            selected_rules=selected_rules,
            pass_value=1 if pass_definition(verifier) else 0,
            verifier_id=verifier.verifier_id,
            verifier_verdict=verifier.verdict,
            verifier_outcome=verifier.outcome,
            verifier_reason_codes=verifier.reason_codes,
            verifier_violated_constraints=verifier.violated_constraints,
            memory_recall_used_ids=[item.memory_id for item in memory_response.items],
            cost_profile=context.get("cost_profile"),
        )

        self._append_eventlog(serialize_eventlog(event_log))

        return RunResult(output=output, verifier=verifier, event_log=event_log)
