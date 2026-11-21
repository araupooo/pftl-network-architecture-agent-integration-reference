# Reproduction

How to reproduce every check in this reference from a fresh clone.
No network access is needed at run time.

## Prerequisites

- `python3` 3.9 or newer (standard library only — no packages to install).
- `git`, `sha256sum` (for the clone and hash steps below).
- No other tools. The scripts read only the vendored
  `data/testnet_vl.json`; nothing is fetched at run time.

## Steps

```sh
git clone https://github.com/araupooo/pftl-network-architecture-agent-integration-reference.git
cd pftl-network-architecture-agent-integration-reference
bash scripts/run_all.sh
```

Expected output ends with:

```
RUN_ALL RESULT: ALL CHECKS PASSED (7/7 scripts)
```

Each script writes its unedited stdout to `outputs/<script>.log`
(`quorum_list`, `peer_network_model`, `unl_overlap`,
`manifest_flood`, `silent_network`, `partition_drill`,
`contract_conformance`). Every log ends with its own
`ALL CHECKS PASSED` line, and no log contains a `FAIL` line.

## Verify the file hashes

```sh
sha256sum -c SHA256SUMS
```

Expected: every file reports `OK`. `SHA256SUMS` covers all scripts,
docs, data, and output logs in the reference.

## Compare against the reference run

The logs in `outputs/` are the unedited stdout of the run that
produced this reference. A fresh run should produce byte-identical
logs. If any line differs, the run is not a reproduction — check the
Python version (`python3 --version`; the reference run used Python
3.12.3) and re-run.

Determinism notes:

- All seven scripts are deterministic: fixed seed (`20261120`) for
  the gossip model, no wall-clock reads, no randomness, no network.
  `unl_overlap.py` reads only the vendored `data/testnet_vl.json`
  (fetched 2026-11-20, re-verified byte-identical to the live URL
  2026-11-21) and compares the list against a fixed reference date,
  `2026-11-21`.
- The `contract_conformance.py` event sequence is a schematic
  reconstruction of the observed flow with shape-faithful placeholder
  values — it checks the proposed contract's rules, not live platform
  behaviour. See `docs/AGENT_INTEGRATION_CONTRACT.md` §1.

## This run

- Date: 2026-11-21, 22:00:28-22:00:29 WIB (fresh clone, this VM, Linux).
- Clone HEAD: `687e9efd2e330989eb72a9e1692b504a386e4e7b` ("Add unedited run logs").
- Python: 3.12.3 (same as the reference run).
- `bash scripts/run_all.sh`: exit 0, `RUN_ALL RESULT: ALL CHECKS PASSED (7/7 scripts)`.
- `sha256sum -c SHA256SUMS`: all 25 files OK (run after `run_all.sh`, so the
  regenerated logs were hashed too).
- `outputs/` comparison: all 8 regenerated logs byte-identical to the shipped
  logs (`diff -r` clean, no differences). No `FAIL` in any log.
- Full repro log: `repro/fresh-clone-run.log`
  (SHA-256 `0e3d217bc980b60bb0068eb34b87483e7d155963c002c0fd46c7904f042439ef`).
