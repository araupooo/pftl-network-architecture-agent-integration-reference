#!/usr/bin/env python3
"""Partition drill (check N-06) — halt-not-fork under the 67% quorum.

Pinned facts:
  - postfiatd quorum: max(ceil(effective*0.67), ceil(total*0.6))
    (ValidatorList.cpp:1934); upstream: max(ceil(effective*0.8),
    ceil(total*0.6)) (rippled master line 1800).
  - Live testnet list: 25 validators (fetched 2026-11-20).
  - xrpl.org consensus docs: "If too many participants are unreachable
    or misbehaving, the network fails to make progress rather than
    diverging or confirming invalid transactions." "As long as fewer
    than 20% of trusted validators are faulty, consensus can continue
    unimpeded; and confirming an invalid transaction would require over
    80% of trusted validators to collude."

Drill: remove validators from the modelled UNL and classify the outcome:
  - remaining >= quorum -> PROGRESS (consensus continues)
  - remaining < quorum, colluding < 80% -> HALT (no fork, no invalid ledger)
  - colluding >= 80% -> INVALID-CONFIRMATION-POSSIBLE

No network, no private data, no randomness. Deterministic.
"""

import math
import sys

N = 25  # live testnet list size


def quorum(total, factor):
    return max(math.ceil(total * factor), math.ceil(total * 0.6))


def classify(remaining, colluding, factor):
    """Outcome for a UNL of size N with `remaining` validators reachable
    and `colluding` of them colluding."""
    q = quorum(N, factor)
    if colluding >= math.ceil(0.8 * N):
        return "INVALID-CONFIRMATION-POSSIBLE"
    if remaining >= q:
        return "PROGRESS"
    return "HALT"


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== partition_drill: halt-not-fork under the 67% quorum ==")
    print(f"UNL N={N}; quorum postfiatd={quorum(N, 0.67)}; upstream={quorum(N, 0.80)}")
    print()

    # --- >20% offline (6 of 25 = 24%) ------------------------------------------
    check("PARTITION: 6 of 25 offline (24%) -> HALT under 80% (19 < 20)",
          classify(19, 0, 0.80) == "HALT")
    check("PARTITION: 6 of 25 offline (24%) -> PROGRESS under 67% (19 >= 17)",
          classify(19, 0, 0.67) == "PROGRESS",
          "the 67% rule tolerates a >20% outage that halts the 80% rule")

    # --- the 67% breaking point ---------------------------------------------------
    check("PARTITION: 8 of 25 offline -> PROGRESS under 67% (17 >= 17)",
          classify(17, 0, 0.67) == "PROGRESS")
    check("PARTITION: 9 of 25 offline (36%) -> HALT under 67% (16 < 17)",
          classify(16, 0, 0.67) == "HALT")
    check("PARTITION: 9 of 25 offline -> HALT under 80% as well",
          classify(16, 0, 0.80) == "HALT")

    # --- >80% colluding -------------------------------------------------------------
    check("PARTITION: 20 of 25 colluding (80%) -> INVALID-CONFIRMATION-POSSIBLE",
          classify(25, 20, 0.67) == "INVALID-CONFIRMATION-POSSIBLE")
    check("PARTITION: 19 of 25 colluding (76%) -> not enough to confirm an "
          "invalid ledger (needs 20)",
          classify(25, 19, 0.67) == "PROGRESS")

    # --- a real partition: the UNL splits into two halves ------------------------------
    print()
    print("-- partition: UNL splits 13 / 12 --")
    print("side A: 13 validators; side B: 12 validators; no cross-partition traffic")
    check("SPLIT: side A (13) cannot reach quorum 17 -> HALT",
          classify(13, 0, 0.67) == "HALT")
    check("SPLIT: side B (12) cannot reach quorum 17 -> HALT",
          classify(12, 0, 0.67) == "HALT")
    check("SPLIT: neither side confirms a divergent ledger (halt, not fork)",
          classify(13, 0, 0.67) == "HALT" and classify(12, 0, 0.67) == "HALT")

    # --- Negative UNL floor: quorum never below 60% of total ------------------------------
    check("FLOOR: quorum at N=25 is at least 60% of total (15)",
          quorum(25, 0.67) >= 15 and quorum(25, 0.80) >= 15)

    print()
    if failures:
        print(f"PARTITION RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("PARTITION RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
