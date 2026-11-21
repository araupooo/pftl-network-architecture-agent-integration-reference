#!/usr/bin/env bash
# run_all.sh — reproduce every check in this reference from a fresh clone.
#
# What it needs (already installed on a normal dev machine):
#   python3 (>= 3.9, standard library only). No other tools, no network.
#   The scripts read only the vendored data/testnet_vl.json; nothing is
#   fetched at run time.
#
# What it runs (in order, each log unedited into outputs/):
#   1. quorum_list.py         — N-01 ValidatorList::calculateQuorum re-derivation
#   2. peer_network_model.py  — N-02 deterministic gossip over pinned parameters
#   3. unl_overlap.py         — N-03 live testnet validator list + overlap map
#   4. manifest_flood.py      — N-04 manifest-flood replay, reject vs evict-oldest
#   5. silent_network.py      — N-05 silent-network liveness detector
#   6. partition_drill.py     — N-06 halt-not-fork partition drill
#   7. contract_conformance.py — N-07 proposed agent-integration contract harness
#
# Exit status: 0 only if every script exits 0; otherwise non-zero.
# Prints a final ALL CHECKS PASSED / FAILED summary.
#
# NOTE: scripts are invoked via `python3` (not `./`) on purpose: files
# uploaded through the GitHub web UI lose their executable bit, so a fresh
# clone would fail with exit 126 if run_all.sh called ./script.py directly.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
mkdir -p outputs
echo "=== run_all.sh ==="
echo "python3: $(python3 --version 2>&1)"
echo "scripts: 7 python3 checks (see outputs/)"

FAILED=""
for script in quorum_list peer_network_model unl_overlap manifest_flood \
              silent_network partition_drill contract_conformance; do
    log="outputs/${script}.log"
    echo "--- running scripts/${script}.py -> ${log} ---"
    if python3 "scripts/${script}.py" > "$log" 2>&1; then
        echo "PASS ${script} (see ${log})"
    else
        echo "FAIL ${script} (see ${log})"
        FAILED="$FAILED $script"
    fi
    echo
done

if [ -n "$FAILED" ]; then
    echo "RUN_ALL RESULT: FAILED — failing scripts:$FAILED"
    exit 1
fi
echo "RUN_ALL RESULT: ALL CHECKS PASSED (7/7 scripts)"
exit 0
