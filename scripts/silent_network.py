#!/usr/bin/env python3
"""Silent-network detector (check N-05) — XRPL halt, 4 Feb 2025.

Incident (reported 2025-02-04/05, CoinDesk / Decrypt / CoinTelegraph /
The Block / BeInCrypto): network activity froze at ledger height
93,927,173/174 for 64 minutes; resumed ~10:58 UTC 4 Feb 2025. "It
looked like consensus was running but validations were not being
published, causing the network to drift apart" (David Schwartz, Ripple
CTO). "One possible failure mode for XRPL is if all the validators
think something's wrong with the network, all refuse to send any
validations, and then there's no chatter to let the network reconverge.
This is the 'silent network' failure." ~88,000 transactions delayed
(XRPSCAN, reported); no assets at risk; "very few UNL validators" made
changes — possibly spontaneous recovery; "only one validator operator
manually intervened" (later updates). All 35 validators were actively
proposing during the incident.

Lesson: validation PUBLICATION is a separate liveness signal from
consensus RUNNING. A topology/propagation monitor must watch
validations-per-ledger, not just ledger close cadence.

Detector: a ledger series is (ledger_index, validations_published,
consensus_rounds_advancing). Flag SILENT-NETWORK when validations are
0 for N consecutive ledgers while consensus rounds keep advancing
(ledgers keep closing). Threshold N=3 consecutive ledgers — a single
ledger with 0 validations is a blip, not a halt.

The incident numbers (64 min, height 93,927,173, ~88k tx) are REPORTED
figures used as test inputs, not measurements made by this script.
No network, no private data, no randomness. Deterministic.
"""

import sys

HEIGHT = 93927173        # reported freeze height (Feb 2025)
HALT_MINUTES = 64        # reported halt duration
TX_DELAYED = 88000       # reported ~88,000 transactions delayed (XRPSCAN)
THRESHOLD = 3            # consecutive zero-validation ledgers -> flag


def detect(series):
    """series: list of (ledger_index, validations_published, rounds_advancing).
    Returns the ledger index where the flag first fires, or None."""
    run = 0
    for idx, validations, advancing in series:
        if validations == 0 and advancing:
            run += 1
            if run >= THRESHOLD:
                return idx - THRESHOLD + 1
        else:
            run = 0
    return None


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== silent_network: validation-publication liveness detector ==")
    print(f"incident reference: height {HEIGHT}, {HALT_MINUTES} min, "
          f"~{TX_DELAYED} tx delayed (reported, Feb 2025)")
    print(f"detector threshold: {THRESHOLD} consecutive zero-validation ledgers "
          f"while consensus advances")
    print()

    # --- healthy series: validations every ledger ---------------------------
    healthy = [(1000 + i, 25, True) for i in range(20)]
    check("HEALTHY: 20 ledgers with 25 validations each -> no flag",
          detect(healthy) is None)

    # --- single-ledger blip: 0 validations once -> no flag --------------------
    blip = [(1000 + i, 25, True) for i in range(5)]
    blip[2] = (1002, 0, True)
    check("BLIP: one ledger with 0 validations -> no flag",
          detect(blip) is None)

    # --- two-ledger gap -> no flag (below threshold) ---------------------------
    gap2 = [(1000 + i, 25, True) for i in range(6)]
    gap2[2] = (1002, 0, True)
    gap2[3] = (1003, 0, True)
    check("GAP-2: two consecutive zero-validation ledgers -> no flag",
          detect(gap2) is None)

    # --- three-ledger gap -> flag at the first zero ledger ----------------------
    gap3 = [(1000 + i, 25, True) for i in range(8)]
    for j in (2, 3, 4):
        gap3[j] = (1000 + j, 0, True)
    check("GAP-3: three consecutive zero-validation ledgers -> flag at 1002",
          detect(gap3) == 1002)

    # --- the Feb 2025 incident shape -------------------------------------------
    # 64 minutes at the 3-5 s ledger cadence = 768-1280 ledgers with
    # validations not being published while ledgers kept closing.
    cadence_low = HALT_MINUTES * 60 // 5    # 768 ledgers at 5 s
    cadence_high = HALT_MINUTES * 60 // 3   # 1280 ledgers at 3 s
    print(f"incident shape: {HALT_MINUTES} min at 3-5 s cadence = "
          f"{cadence_low}-{cadence_high} ledgers with 0 validations")
    check("INCIDENT: 64 min at 5 s cadence is 768 ledgers",
          cadence_low == 768)
    check("INCIDENT: 64 min at 3 s cadence is 1280 ledgers",
          cadence_high == 1280)
    incident = [(HEIGHT + i, 0, True) for i in range(cadence_low)]
    check("INCIDENT: the Feb 2025 shape flags at the freeze height",
          detect(incident) == HEIGHT)

    # --- halted consensus (no rounds advancing) is a different failure ---------
    stalled = [(1000 + i, 0, False) for i in range(5)]
    check("STALLED: 0 validations with consensus NOT advancing -> no "
          "SILENT-NETWORK flag (different failure class)",
          detect(stalled) is None)

    print()
    if failures:
        print(f"SILENT RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("SILENT RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
