#!/usr/bin/env python3
"""Agent-integration contract conformance harness (check N-07).

The integration surface has NO public specification: the landing page at
https://tasknode.postfiat.org/ (fetched 2026-11-20) renders only the text
"What are you working on?" — no docs, no API reference, no public
repository was found. The contract in docs/AGENT_INTEGRATION_CONTRACT.md
is therefore a PROPOSAL, derived from the OBSERVED evidence-delivery
flow, not a specification of the platform. This script does NOT test the
live platform (no network, no login). It tests the proposal itself:
given the observed event sequence, do the proposed schema rules hold,
and do they reject the malformed sequences they are supposed to reject?

Observed flow (research report 2026-11-20, section 4):
  Offered -> Accepted -> Submitted -> verification requested ->
  verification response -> settlement outcome.
  Evidence types observed: URL, commit (commit/PR URL), text.
  Settlement outcomes carry: value, completion score, evidence score,
  transaction hash, CID.
The SEQUENCE below is a SCHEMATIC reconstruction of that observed flow
with shape-faithful placeholder values (a 64-hex transaction hash, a
CID-shaped string, numeric scores) — it is not a transcript of any real
task, and no real task identifier, account, or value from a real task
appears in it. What the script proves is that the PROPOSED contract's
rules are internally consistent and discriminating, so that when the
platform publishes a real specification, the same harness can be pointed
at real event data.

Proposed contract version: pf.contract.v1-proposal (2026-11-21).
Rules enforced:
  R1  event order is Offered, Accepted, Submitted, then any number of
      (verification_request, verification_response) pairs, then at most
      one settlement event.
  R2  every evidence item has kind url | commit | text and a non-empty ref.
  R3  every verification_request is answered by exactly one
      verification_response before any settlement event.
  R4  a settlement event carries value (number), completion_score (0-100),
      evidence_score (0-100), tx_hash (64 hex chars), cid (non-empty).
  R5  no settlement event may appear before the verification round-trip
      closes.

No network, no private data, no randomness. Deterministic.
"""

import re
import sys

SCHEMA_VERSION = "pf.contract.v1-proposal"

EVIDENCE_KINDS = {"url", "commit", "text"}
TX_HASH_RE = re.compile(r"^[0-9a-f]{64}$")

# --- the observed flow, as a schematic sequence ---------------------------
# Placeholder values are shape-faithful only: "aaaa..." is a 64-hex
# string, "bafy..." is a CID-shaped string, scores are in 0-100.
SEQUENCE = [
    {"type": "task.offered", "task_id": "example-task-001",
     "title": "Example network-architecture reference", "value": 5,
     "scale": "personal"},
    {"type": "task.accepted", "task_id": "example-task-001"},
    {"type": "task.submitted", "task_id": "example-task-001",
     "evidence": [
         {"kind": "url", "ref": "https://example.invalid/repo",
          "note": "public reference repository"},
         {"kind": "commit", "ref": "https://example.invalid/repo/commit/0123456789abcdef",
          "note": "pinned commit of the reference"},
         {"kind": "text", "ref": "Summary of findings, with measured values.",
          "note": "text summary"},
     ]},
    {"type": "task.verification_requested", "task_id": "example-task-001",
     "question": "Quote the in-code quorum comment verbatim."},
    {"type": "task.verification_response", "task_id": "example-task-001",
     "answer": "Use a 67% quorum to balance fork safety, liveness, and "
               "required UNL overlap.",
     "cites": ["ValidatorList.cpp:1898-1901"]},
    {"type": "task.settlement", "task_id": "example-task-001",
     "value": 5, "completion_score": 100, "evidence_score": 92,
     "tx_hash": "a" * 64, "cid": "bafybeigdyrzt5sfp7udm7hu76uh7y26nf3efuylqabf3oclgtqy55fbzdi"},
]


def check_sequence(seq):
    """Validate one event sequence against rules R1-R5.
    Returns a list of violation strings (empty = conformant)."""
    violations = []
    seen = {"offered": False, "accepted": False, "submitted": False,
            "settlement": False}
    open_requests = 0
    order = ["task.offered", "task.accepted", "task.submitted"]

    for i, ev in enumerate(seq):
        t = ev.get("type")
        if t in order:
            if seen[t.split(".")[1]]:
                violations.append(f"event {i}: duplicate {t}")
            # order: offered must precede accepted, accepted precede submitted
            if t == "task.accepted" and not seen["offered"]:
                violations.append(f"event {i}: accepted before offered")
            if t == "task.submitted" and not seen["accepted"]:
                violations.append(f"event {i}: submitted before accepted")
            seen[t.split(".")[1]] = True
        elif t == "task.verification_requested":
            if not seen["submitted"]:
                violations.append(f"event {i}: verification requested before delivery")
            if seen["settlement"]:
                violations.append(f"event {i}: verification requested after settlement")
            if not isinstance(ev.get("question"), str) or not ev.get("question"):
                violations.append(f"event {i}: verification request has no question")
            open_requests += 1
        elif t == "task.verification_response":
            if open_requests < 1:
                violations.append(f"event {i}: verification response with no open request")
            else:
                open_requests -= 1
            if not isinstance(ev.get("answer"), str) or not ev.get("answer"):
                violations.append(f"event {i}: verification response has no answer")
        elif t == "task.settlement":
            if seen["settlement"]:
                violations.append(f"event {i}: second settlement event")
            if open_requests > 0:
                violations.append(f"event {i}: settlement while {open_requests} "
                                  f"verification request(s) unanswered (R5)")
            seen["settlement"] = True
            # R4: required fields and shapes
            if not isinstance(ev.get("value"), (int, float)):
                violations.append(f"event {i}: settlement value is not a number")
            for field in ("completion_score", "evidence_score"):
                v = ev.get(field)
                if not isinstance(v, (int, float)) or not (0 <= v <= 100):
                    violations.append(f"event {i}: settlement {field} missing or "
                                      f"outside 0-100: {v!r}")
            if not TX_HASH_RE.match(str(ev.get("tx_hash", ""))):
                violations.append(f"event {i}: settlement tx_hash is not 64 hex chars")
            if not isinstance(ev.get("cid"), str) or not ev.get("cid"):
                violations.append(f"event {i}: settlement cid missing or empty")
        else:
            violations.append(f"event {i}: unknown event type {t!r}")

    # R2: evidence items, checked on the submitted event
    for i, ev in enumerate(seq):
        if ev.get("type") == "task.submitted":
            items = ev.get("evidence")
            if not isinstance(items, list) or not items:
                violations.append(f"event {i}: delivery carries no evidence items")
                continue
            for j, item in enumerate(items):
                if item.get("kind") not in EVIDENCE_KINDS:
                    violations.append(f"event {i} evidence {j}: kind "
                                      f"{item.get('kind')!r} not in url/commit/text (R2)")
                if not isinstance(item.get("ref"), str) or not item.get("ref"):
                    violations.append(f"event {i} evidence {j}: empty ref (R2)")

    if open_requests > 0:
        violations.append(f"sequence ends with {open_requests} unanswered "
                          f"verification request(s) (R3)")
    return violations


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== contract_conformance: proposed agent-integration contract ==")
    print(f"contract version: {SCHEMA_VERSION} (PROPOSAL — no public spec exists)")
    print(f"evidence kinds: {sorted(EVIDENCE_KINDS)}; "
          f"sequence: {len(SEQUENCE)} events")
    print()

    # --- the observed flow conforms -----------------------------------------
    v = check_sequence(SEQUENCE)
    check("POSITIVE: the observed flow sequence conforms to the proposed contract",
          v == [], f"violations: {v}" if v else "0 violations")
    check("POSITIVE: the sequence carries all three observed evidence kinds",
          {i["kind"] for i in SEQUENCE[2]["evidence"]} == EVIDENCE_KINDS)
    check("POSITIVE: the settlement event carries all five required fields",
          all(k in SEQUENCE[-1] for k in
              ("value", "completion_score", "evidence_score", "tx_hash", "cid")))

    # --- negative cases: the harness must reject malformed sequences --------
    def mutated(fn, label):
        import copy
        seq = copy.deepcopy(SEQUENCE)
        fn(seq)
        return check_sequence(seq), label

    neg = []

    def drop_settlement_field(seq):
        del seq[-1]["tx_hash"]
    neg.append(mutated(drop_settlement_field, "settlement without tx_hash"))

    def bad_kind(seq):
        seq[2]["evidence"][0]["kind"] = "screenshot"
    neg.append(mutated(bad_kind, "evidence kind 'screenshot'"))

    def settlement_before_response(seq):
        seq.insert(4, seq.pop())  # move settlement before the verification response
    neg.append(mutated(settlement_before_response, "settlement before verification response"))

    def double_response(seq):
        seq.insert(5, dict(seq[4]))
    neg.append(mutated(double_response, "two responses to one request"))

    def score_over_100(seq):
        seq[-1]["completion_score"] = 101
    neg.append(mutated(score_over_100, "completion_score 101"))

    def no_evidence(seq):
        seq[2]["evidence"] = []
    neg.append(mutated(no_evidence, "delivery with no evidence"))

    for violations, label in neg:
        check(f"NEGATIVE: {label} is rejected",
              len(violations) > 0,
              f"{len(violations)} violation(s): {violations[0] if violations else ''}")

    # --- liveness rule: a submitted task with no platform message is flagged --
    print()
    print("-- liveness: submitted, no platform message -> flagged, not assumed done --")
    stalled = [e for e in SEQUENCE[:3]]  # offered, accepted, submitted only
    v_stalled = check_sequence(stalled)
    check("LIVENESS: a sequence ending at delivery has no violations of "
          "shape, but carries no settlement",
          v_stalled == [] and not any(e["type"] == "task.settlement" for e in stalled),
          "shape-conformant yet incomplete: the harness reports 'no settlement "
          "event', it does not infer one")

    print()
    if failures:
        print(f"CONTRACT RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("CONTRACT RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
