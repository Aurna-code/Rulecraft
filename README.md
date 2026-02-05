# Rulecraft

Rulecraft Development

Spec guidance: the `spec/` directory is the single source of truth.

## Overview
Rulecraft is an orchestration layer that wraps LLM calls with policy, memory recall, verification, and logging.
This repository contains a minimal MVP implementation that follows the Playbook, SSOT, Verifier Spec, and Addendum
principles (Runner + LLMAdapter + VerifierAdapter + Logger/EventLog).

## Quick start

```python
from rulecraft import RulecraftRunner
from rulecraft.adapters import EchoLLMAdapter
from rulecraft.verifier import BasicVerifier

runner = RulecraftRunner(
    llm_adapter=EchoLLMAdapter(),
    verifier=BasicVerifier(),
)

result = runner.run(
    prompt="Draft a short status update.",
    context={"bucket_key": "I1|general|clarity_high"},
)

print(result.output)
print(result.event_log.pass_value)
```

## Design alignment
- **Runner/Adapters**: `RulecraftRunner` coordinates LLM calls, memory recall, verification, and event logging.
- **Verifier**: `BasicVerifier` performs deterministic L1 checks and returns a `VerifierResult` with SSOT-compliant fields.
- **PASS definition**: `pass_definition()` implements `PASS iff verdict == PASS and outcome != FAIL`.
- **Memory**: `MemoryStore.recall()` implements filter → rerank recall for ReasoningBank/Rulebook/ReuseBuffer items.
