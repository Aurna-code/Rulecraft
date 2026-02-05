"""Rule selection helpers."""

from __future__ import annotations

from rulecraft.rules import RuleStore


class CandidateSelector:
    def __init__(self, rule_store: RuleStore | None = None) -> None:
        self.rule_store = rule_store or RuleStore()

    def select(self, context: dict, memory_response) -> list[dict]:
        if context.get("selected_rules"):
            return context["selected_rules"]

        bucket_key = context.get("bucket_key", "")
        bucket_prefix = bucket_key.split("|")[0] if bucket_key else ""
        domain_tag = bucket_key.split("|")[1] if "|" in bucket_key else ""

        selected: list[dict] = []
        for rule in self.rule_store.rules:
            if rule.bucket_scope and bucket_prefix not in rule.bucket_scope:
                continue
            if domain_tag and rule.tags and domain_tag not in rule.tags:
                continue
            selected.append({"rule_id": rule.rule_id, "version": rule.version, "type": rule.type})
            if len(selected) >= 3:
                break

        if memory_response.items:
            selected.append({"rule_id": "memory_hint", "version": "0.1", "type": "memory"})

        return selected
