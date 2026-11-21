#!/usr/bin/env python3
"""Re-derive ValidatorList::calculateQuorum (check N-01).

Pinned sources (postfiatd main HEAD 0085a1ff, 2026-10-10):
  src/xrpld/app/misc/detail/ValidatorList.cpp:1845 (calculateQuorum)
  src/xrpld/app/misc/detail/ValidatorList.cpp:1898-1901 (comment, verbatim):
      "Use a 67% quorum to balance fork safety, liveness, and required UNL
       overlap. Note: Original XRPL uses 80%, but this fork uses 67% for
       devnet/testnet. For mainnet, this should be reverted to 80%."
  src/xrpld/app/misc/detail/ValidatorList.cpp:1934 (formula):
      max(ceil(effectiveUnlSize * 0.67), ceil(unlSize * 0.6))
  src/xrpld/app/misc/ValidatorList.h:170:
      "Otherwise, the trusted list size is set to 125% of the quorum."
  src/xrpld/app/misc/detail/ValidatorList.cpp:2109:
      quorum_ = calculateQuorum(unlSize, effectiveUnlSize, seenSize)
Upstream rippled master (fetched 2026-11-20):
  src/xrpld/app/misc/detail/ValidatorList.cpp:1765 (80% comment),
  line 1800: max(ceil(effectiveUnlSize * 0.8), ceil(unlSize * 0.6))
Theorem 8 (Chase & MacBrough, arXiv:1802.07242), quoted in both
codebases: fork safety if Oi,j > nj/2 + ni - qi + ti,j. With qi = 0.67*ni
the proof allows < 0.33*ni unique validators between two UNLs; with
qi = 0.8*ni it allows < 0.2*ni (per the postfiatd code comment).

Live testnet list (fetched 2026-11-20, data/testnet_vl.json):
  publisher ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2
  sequence 30, effective 2026-11-17T20:10:08Z, expiration 2028-03-31T16:14:53Z,
  25 validators, all with manifests.

No network, no private data, no randomness. Deterministic output.
"""

import math
import sys


def quorum(effective, total, factor):
    """calculateQuorum: max(ceil(effective * factor), ceil(total * 0.6))."""
    return max(math.ceil(effective * factor), math.ceil(total * 0.6))


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== quorum_list: ValidatorList::calculateQuorum re-derivation ==")
    print("postfiatd: max(ceil(effective*0.67), ceil(total*0.6))")
    print("upstream : max(ceil(effective*0.8),  ceil(total*0.6))")
    print()

    # --- the live testnet list (N=25) ------------------------------------
    n = 25
    q67 = quorum(n, n, 0.67)
    q80 = quorum(n, n, 0.80)
    print(f"live testnet UNL N={n}: postfiatd quorum={q67}, upstream quorum={q80}, gap={q80 - q67}")
    check("TESTNET: postfiatd quorum at N=25 is 17", q67 == 17,
          f"max(ceil(25*0.67)=17, ceil(25*0.6)=15)")
    check("TESTNET: upstream quorum at N=25 is 20", q80 == 20,
          f"max(ceil(25*0.8)=20, ceil(25*0.6)=15)")
    check("TESTNET: trusted-list size at N=25 is 125% of quorum (single list: all trusted)",
          math.ceil(q67 * 1.25) == 22, "ceil(17*1.25)=22 (multi-list rule, ValidatorList.h:170)")

    # --- the 60% floor binds for small UNLs --------------------------------
    check("FLOOR: at N=2 the quorum equals the 60% floor (2) under both rules",
          quorum(2, 2, 0.67) == 2 and quorum(2, 2, 0.80) == 2,
          "postfiatd max(ceil(1.34)=2, ceil(1.2)=2)=2; upstream max(ceil(1.6)=2, 2)=2")
    check("FLOOR: postfiatd quorum never drops below 60% of total (N=1..200)",
          all(quorum(x, x, 0.67) >= math.ceil(x * 0.6) for x in range(1, 201)))
    check("FLOOR: upstream quorum never drops below 60% of total (N=1..200)",
          all(quorum(x, x, 0.80) >= math.ceil(x * 0.6) for x in range(1, 201)))

    # --- divergence across sizes -------------------------------------------
    check("DIVERGENCE: postfiatd quorum <= upstream quorum for every N=1..200",
          all(quorum(x, x, 0.67) <= quorum(x, x, 0.80) for x in range(1, 201)))
    check("DIVERGENCE: postfiatd quorum is strictly lower for N>=4 except N=5, N=6",
          all(quorum(x, x, 0.67) < quorum(x, x, 0.80)
              for x in range(4, 201) if x not in (5, 6)),
          "N=5: ceil(5*0.67)=4 = ceil(5*0.8)=4; N=6: ceil(6*0.67)=5 = ceil(6*0.8)=5 "
          "(the 60% floor and ceiling rounding coincide)")

    # --- offline tolerance: how many validators can go dark -----------------
    # quorum is computed over the EFFECTIVE (seen) set; with `off` offline
    # the remaining set must still reach quorum. Tolerance = max offline
    # count such that (N - off) >= quorum(N, N).
    def max_offline(total, factor):
        q = quorum(total, total, factor)
        return total - q
    print()
    print("-- offline tolerance (validators that can go dark, quorum still met) --")
    for total in (25, 35, 100):
        o67 = max_offline(total, 0.67)
        o80 = max_offline(total, 0.80)
        print(f"N={total}: postfiatd tolerates {o67} offline ({100.0 * o67 / total:.0f}%); "
              f"upstream tolerates {o80} offline ({100.0 * o80 / total:.0f}%)")
    check("TOLERANCE: at N=25 postfiatd tolerates 8 offline, upstream 5",
          max_offline(25, 0.67) == 8 and max_offline(25, 0.80) == 5)
    check("TOLERANCE: at N=35 postfiatd tolerates 11 offline, upstream 7",
          max_offline(35, 0.67) == 11 and max_offline(35, 0.80) == 7)

    # --- fork-safety margin (Theorem 8, per the code comment) ---------------
    print()
    print("-- fork-safety margin (unique validators two UNLs may have) --")
    print("postfiatd qi=0.67*ni: two UNLs may have < 0.33*ni unique validators")
    print("upstream  qi=0.80*ni: two UNLs may have < 0.20*ni unique validators")
    check("MARGIN: 0.33*25 = 8.25 unique validators allowed under 67%",
          0.33 * 25 == 8.25)
    check("MARGIN: 0.20*25 = 5.0 unique validators allowed under 80%",
          0.20 * 25 == 5.0)
    check("MARGIN: the 67% rule admits 3.25 more unique validators at N=25",
          0.33 * 25 - 0.20 * 25 == 3.25)

    print()
    print("== quorum table (N, postfiatd, upstream) ==")
    print(f"{'N':>4} {'postfiatd':>10} {'upstream':>9}")
    for total in (1, 2, 3, 5, 10, 16, 25, 35, 36, 100, 200):
        print(f"{total:>4} {quorum(total, total, 0.67):>10} {quorum(total, total, 0.80):>9}")

    print()
    if failures:
        print(f"QUORUM RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("QUORUM RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
