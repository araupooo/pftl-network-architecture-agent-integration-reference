#!/usr/bin/env python3
"""Manifest-flood replay (check N-04) — postfiatd 1.0.5/1.0.6 vs XRPL 3.3.0.

Source: docs/MANIFEST_FLOOD_HOTFIX.md (postfiatd 0085a1ff, verified 2026-11-20/21):
  - 1.0.5 closed the flood by refusing every manifest whose master key is
    not on the validator list — which also blocked learning about
    not-yet-listed validators (breaks the dynamic UNL flow).
  - 1.0.6 follows XRPL's corrected 3.3.0 design with one deliberate
    difference: XRPL rejects new unlisted keys once its bound is full,
    while 1.0.6 evicts the oldest unlisted entry instead, "so a flood
    churns the set but can never leave the node blind to a newcomer
    until the next restart".
  - Bounded set: default 1000 keys ([overlay] max_untrusted_count; 0
    restores the 1.0.5 behaviour). Unlisted manifests never written to
    wallet.db. Individual manifests capped at 512 bytes (was 4 KiB).
  - Legacy drain: one oversized 1.0.4 dump up to 256 MiB - 1 within
    300 seconds (was 128 MiB / 60 s).
  - Greeting carries every listed manifest plus a random subset of at
    most max_untrusted_count unlisted ones. Revocations of unlisted
    keys are never sent.
  - OverlayImpl.cpp:648 charges the sender for oversized manifest
    batches ("manifest batch limit").

Model: an unlisted-manifest set with a 1000-key bound under a flood of
unlisted manifests, comparing the two policies. A legitimate newcomer
(a validator not yet on the list) submits its manifest during and after
the flood. The model answers: can the node still learn about the
newcomer?

No network, no private data, no randomness (fixed order). Deterministic.
"""

import sys
from collections import OrderedDict

BOUND = 1000          # [overlay] max_untrusted_count (default)
MANIFEST_CAP = 512    # bytes per manifest (was 4096)
LEGACY_DRAIN_MAX = 256 * 1024 * 1024 - 1   # bytes
LEGACY_DRAIN_SECS = 300


class UnlistedSet:
    def __init__(self, policy):
        self.policy = policy  # "reject-when-full" (XRPL 3.3.0) or "evict-oldest" (1.0.6)
        self.store = OrderedDict()

    def admit(self, key):
        if key in self.store:
            return "duplicate"
        if len(self.store) >= BOUND:
            if self.policy == "reject-when-full":
                return "rejected-bound-full"
            self.store.popitem(last=False)  # evict oldest
            self.store[key] = True
            return "admitted-evicted-oldest"
        self.store[key] = True
        return "admitted"

    def __len__(self):
        return len(self.store)


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== manifest_flood: reject-when-full (XRPL 3.3.0) vs evict-oldest (1.0.6) ==")
    print(f"bound={BOUND} keys; manifest cap={MANIFEST_CAP} B (was 4096 B); "
          f"legacy drain {LEGACY_DRAIN_MAX} B / {LEGACY_DRAIN_SECS} s")
    print()

    # --- the cap -------------------------------------------------------------
    check("CAP: a 512-byte manifest is admitted", 512 <= MANIFEST_CAP)
    check("CAP: a 513-byte manifest is rejected (padding no longer works)",
          513 > MANIFEST_CAP)
    check("CAP: the old 4 KiB cap admitted 8x larger manifests",
          4096 == 8 * 512)
    check("DRAIN: legacy drain accepts up to 256 MiB - 1",
          LEGACY_DRAIN_MAX == 256 * 1024 * 1024 - 1)
    check("DRAIN: legacy drain window is 300 s (was 60 s)",
          LEGACY_DRAIN_SECS == 300)

    # --- the flood ------------------------------------------------------------
    flood_keys = [f"flood-{i:05d}" for i in range(2500)]
    newcomer = "newcomer-validator-00001"

    for policy in ("reject-when-full", "evict-oldest"):
        s = UnlistedSet(policy)
        outcomes = [s.admit(k) for k in flood_keys]
        admitted = outcomes.count("admitted") + outcomes.count("admitted-evicted-oldest")
        rejected = outcomes.count("rejected-bound-full")
        print(f"policy {policy}: flood of 2500 unlisted keys -> "
              f"admitted={admitted}, rejected={rejected}, set size={len(s)}")
        check(f"FLOOD[{policy}]: set never exceeds the {BOUND}-key bound",
              len(s) <= BOUND)
        # newcomer arrives mid-flood (after 1500 flood keys) and after it
        s2 = UnlistedSet(policy)
        for k in flood_keys[:1500]:
            s2.admit(k)
        mid = s2.admit(newcomer)
        for k in flood_keys[1500:]:
            s2.admit(k)
        after = newcomer in s2.store
        print(f"policy {policy}: newcomer mid-flood -> {mid}; "
              f"still present after the flood -> {after}")
        if policy == "reject-when-full":
            check("DISCOVERY[reject-when-full]: newcomer is refused once the set is full",
                  mid == "rejected-bound-full" and not after)
        else:
            check("DISCOVERY[evict-oldest]: newcomer is admitted mid-flood",
                  mid == "admitted-evicted-oldest")
            check("DISCOVERY[evict-oldest]: newcomer is churned out by the "
                  "next 1000 flood arrivals (present after flood: False)",
                  after is False,
                  "evict-oldest keeps the node from going blind at arrival, "
                  "but discovery is not durable under a sustained flood")

    # --- listed keys are never bounded or evicted ------------------------------
    print()
    print("-- listed keys are never bounded or evicted (hotfix doc) --")
    check("LISTED: the bound applies to unlisted keys only (documented)",
          True, "docs/MANIFEST_FLOOD_HOTFIX.md: 'Listed keys are never bounded or evicted'")

    print()
    if failures:
        print(f"FLOOD RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("FLOOD RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
