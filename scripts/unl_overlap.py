#!/usr/bin/env python3
"""UNL-overlap map from the live testnet validator list (check N-03).

Live list (public, no auth): https://postfiat.org/testnet_vl.json
Documented in docs/NodeSetup.md:114-122:
  [validator_list_sites] https://postfiat.org/testnet_vl.json
  [validator_list_keys]
      ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2
  [validator_list_threshold] 0
Vendored copy (fetched 2026-11-20, re-verified byte-identical against the
live URL on 2026-11-21): data/testnet_vl.json. This script reads ONLY the
vendored copy — no network at run time — so its output is deterministic.
The live URL is recorded here for the reader to re-check by hand.

AS_OF = "2026-11-21"  # fixed reference date: the list was fetched 2026-11-20
                       # and re-verified identical to the live URL 2026-11-21

Theorem 8 (Chase & MacBrough, arXiv:1802.07242), quoted in
ValidatorList.cpp: fork safety if Oi,j > nj/2 + ni - qi + ti,j, where
Oi,j is the overlap between two UNLs, ni/nj their sizes, qi the quorum
for Pi's UNL, and ti,j the tolerated Byzantine faults. With qi = 0.67*ni
the proof allows < 0.33*ni unique validators between two UNLs; with
qi = 0.8*ni it allows < 0.2*ni (per the postfiatd code comment).

The live list is a SINGLE list of 25 validators, so pairwise overlap is
computed over hypothetical second UNLs of varying overlap against the
live list — the map shows where fork safety holds and fails under each
quorum rule. The XRPL 35-validator default UNL is the reference design,
not PFTL's live set.

No private data, no randomness, no network. Fully deterministic output.
"""

import base64
import datetime
import json
import math
import os
import sys

VL_URL = "https://postfiat.org/testnet_vl.json"  # reference only; never fetched here
VENDORED = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "data", "testnet_vl.json")
DOCUMENTED_PUBLISHER = "ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2"
EPOCH = datetime.datetime(2000, 1, 1, tzinfo=datetime.timezone.utc)
AS_OF = "2026-11-21"  # fixed reference date (see header)


def ripple_ts(x):
    return (EPOCH + datetime.timedelta(seconds=x)).isoformat() if x else None


def load_list():
    """Read the vendored copy only. No network at run time."""
    with open(VENDORED, "rb") as f:
        return json.load(f), "vendored copy data/testnet_vl.json (fetched 2026-11-20, " \
                           "re-verified byte-identical to the live URL 2026-11-21)"


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== unl_overlap: live testnet validator list + overlap map ==")
    doc, source = load_list()
    print(f"source: {source}")
    print(f"reference date (fixed): {AS_OF}")
    print(f"list version: {doc.get('version')}")
    print(f"publisher key: {doc.get('public_key')}")
    check("VL: publisher key matches the documented key in NodeSetup.md",
          doc.get("public_key") == DOCUMENTED_PUBLISHER)

    blob_entry = doc["blobs_v2"][0]
    inner = json.loads(base64.b64decode(blob_entry["blob"]))
    validators = inner.get("validators", [])
    n = len(validators)
    print(f"sequence: {inner.get('sequence')}")
    print(f"effective: {ripple_ts(inner.get('effective'))}")
    print(f"expiration: {ripple_ts(inner.get('expiration'))}")
    print(f"validators in list: {n}")
    check("VL: list carries 25 validators", n == 25)
    check("VL: every validator carries a manifest",
          all(v.get("manifest") for v in validators))
    check("VL: sequence is 30", inner.get("sequence") == 30)
    check("VL: list is effective at the reference date (effective < 2026-11-21 < expiration)",
          inner.get("effective") and inner.get("expiration")
          and ripple_ts(inner.get("effective")) < AS_OF
          < ripple_ts(inner.get("expiration")),
          f"effective {ripple_ts(inner.get('effective'))}; expiration "
          f"{ripple_ts(inner.get('expiration'))}")

    keys = [v["validation_public_key"] for v in validators]
    check("VL: all 25 validator keys are distinct", len(set(keys)) == 25)
    check("VL: all keys are ED-prefixed hex", all(k.startswith("ED") for k in keys))

    # --- quorum numbers for the live list ---------------------------------
    def quorum(effective, total, factor):
        return max(math.ceil(effective * factor), math.ceil(total * 0.6))

    q67, q80 = quorum(n, n, 0.67), quorum(n, n, 0.80)
    print(f"quorum at N={n}: postfiatd 67% -> {q67}; upstream 80% -> {q80}")
    check("QUORUM: live list needs 17 of 25 under 67%", q67 == 17)
    check("QUORUM: live list needs 20 of 25 under 80%", q80 == 20)

    # --- Theorem 8 overlap map ----------------------------------------------
    # The code comment (ValidatorList.cpp:1898-1934) derives from Theorem 8:
    # with qi = 0.67*ni, two UNLs may have < 0.33*ni unique validators
    # between them (pi + pj < 0.33*ni); with qi = 0.8*ni, < 0.20*ni.
    # For two equal UNLs of size 25 with p unique validators each side,
    # overlap O = 25 - p and pi + pj = 2p. The script checks the comment's
    # OWN derived bound, not a re-derivation of Theorem 8 itself.
    print()
    print("-- Theorem 8 overlap map (two UNLs of size 25, p unique each side) --")
    print("postfiatd 67%: pi+pj < 0.33*25 = 8.25  ->  p <= 4  ->  overlap >= 21")
    print("upstream  80%: pi+pj < 0.20*25 = 5.0   ->  p <= 2  ->  overlap >= 23")
    for overlap in (25, 23, 22, 21, 20, 18):
        p = 25 - overlap
        safe67 = 2 * p < 0.33 * 25
        safe80 = 2 * p < 0.20 * 25
        print(f"overlap O={overlap}/25 (p={p} unique each side): "
              f"fork-safe under 67%? {safe67}; under 80%? {safe80}")
    check("OVERLAP: O=25 (identical UNLs) is fork-safe under both rules",
          2 * 0 < 0.33 * 25 and 2 * 0 < 0.20 * 25)
    check("OVERLAP: O=23 is fork-safe under 80% (2p=4 < 5.0)",
          2 * 2 < 0.20 * 25)
    check("OVERLAP: O=22 is fork-safe under 67% (2p=6 < 8.25) but NOT under 80% (6 > 5.0)",
          2 * 3 < 0.33 * 25 and not (2 * 3 < 0.20 * 25))
    check("OVERLAP: O=21 is the minimum fork-safe overlap under 67% (2p=8 < 8.25)",
          2 * 4 < 0.33 * 25)
    check("OVERLAP: O=20 is NOT fork-safe under 67% (2p=10 > 8.25)",
          not (2 * 5 < 0.33 * 25))
    check("OVERLAP: the 67% rule admits 2 more unique validators per side than 80% (4 vs 2)",
          4 - 2 == 2)

    print()
    if failures:
        print(f"OVERLAP RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("OVERLAP RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
