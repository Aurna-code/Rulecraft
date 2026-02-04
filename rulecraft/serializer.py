"""Serialization helpers for dotted-key JSONL outputs."""

from __future__ import annotations

from dataclasses import asdict

from rulecraft.schemas import EventLog


def serialize_eventlog(event_log: EventLog) -> dict:
    payload = asdict(event_log)
    payload["run.mode"] = payload.pop("run_mode")
    return payload
