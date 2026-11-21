# PFTL Network-Architecture and Agent-Integration Reference

An inspectable reference for the PFTL network (the postfiatd fork of
rippled) and a proposed machine-readable contract for agent integration
with the task platform. Every substantive claim is labelled
[FAKTA] (verified, source + date), [ESTIMASI] (modelled/reported number),
or [ANALISIS] (interpretation), and every claim is mapped to a runnable
check and a pinned primary source in `docs/CLAIMS.md`.

## What this reference proves

[FAKTA] The PFTL validator-list quorum is 67%, not the upstream 80% —
a second, distinct 67% divergence from the amendment threshold (67/100).
The in-code comment itself says the value is for devnet/testnet and
"should be reverted to 80%" for mainnet. At the live testnet list size
(25 validators) the quorum is 17 under the 67% rule vs 20 under the 80%
rule, and two UNLs may share as few as 21 of 25 validators and stay
fork-safe under 67%, vs 23 of 25 under 80%.

[FAKTA] The overlay's peer-slot, squelch, send-queue, and manifest
parameters are pinned from the postfiatd source at commit `0085a1ff`
and reproduced by a deterministic gossip model: a validation reaches
all 25 testnet validators within the 3–5 s ledger cadence, and the
network halts rather than forks when a partition removes quorum.

[FAKTA] The postfiatd manifest-flood hotfix (1.0.5/1.0.6) bounds
unlisted manifests at 1000 keys and 512 bytes each, and evicts the
oldest entry when full — unlike upstream, which rejects new keys once
full. The replay in this reference shows the trade-off precisely:
evict-oldest never leaves the node blind to a newcomer at arrival, but
a sustained flood churns the newcomer out again.

[ANALISIS] The agent-integration contract in
`docs/AGENT_INTEGRATION_CONTRACT.md` is a labelled PROPOSAL. No public
specification exists — the platform's public page renders a single
prompt line and no API reference — so the contract is derived from the
observable evidence-delivery flow (URL / commit / text evidence,
verification round-trip, settlement outcome) and checked by a
conformance harness, not presented as the platform's specified API.

## How to run it

```sh
bash scripts/run_all.sh
```

Python 3.9+ standard library only; no network at run time — the
scripts read only the vendored `data/testnet_vl.json`. Each script
prints PASS/FAIL per check and writes its unedited stdout to
`outputs/<script>.log`. The runner exits non-zero if any script fails
and prints a final `ALL CHECKS PASSED` / `FAILED` summary.

## File map

| Path | Contents |
|---|---|
| `scripts/quorum_list.py` | N-01: re-derivation of `ValidatorList::calculateQuorum` (67% vs 80%) |
| `scripts/peer_network_model.py` | N-02: deterministic gossip model over the pinned peer parameters |
| `scripts/unl_overlap.py` | N-03: live testnet validator list + Theorem 8 overlap map |
| `scripts/manifest_flood.py` | N-04: manifest-flood replay, reject-when-full vs evict-oldest |
| `scripts/silent_network.py` | N-05: silent-network liveness detector (Feb 2025 halt shape) |
| `scripts/partition_drill.py` | N-06: halt-not-fork partition drill under the 67% quorum |
| `scripts/contract_conformance.py` | N-07: conformance harness for the proposed integration contract |
| `scripts/run_all.sh` | Runs all seven checks, captures unedited logs to `outputs/` |
| `data/testnet_vl.json` | Vendored testnet validator list, fetched 2026-11-20, re-verified byte-identical to the live URL 2026-11-21 |
| `outputs/` | Unedited logs from the latest `run_all.sh` run (7/7 passed) |
| `docs/NETWORK_ARCHITECTURE.md` | The network-architecture reference |
| `docs/AGENT_INTEGRATION_CONTRACT.md` | The proposed agent-integration contract (PROPOSAL) |
| `docs/CLAIMS.md` | Claim-to-check-to-source index |
| `docs/SOURCES.md` | Pinned primary sources |
| `docs/REPRODUCTION.md` | Fresh-clone reproduction steps |
| `docs/FAILURE_MODES.md` | Failure-mode catalogue and operator implications |
| `SHA256SUMS` | SHA-256 of every file in this reference (`sha256sum -c SHA256SUMS`) |

## Pinned sources

- postfiatd at commit `0085a1ff` (2026-10-10): `src/xrpld/app/misc/detail/ValidatorList.cpp`,
  `src/xrpld/overlay/`, `src/xrpld/peerfinder/`, `docs/MANIFEST_FLOOD_HOTFIX.md`,
  `docs/NodeSetup.md`, `docs/dynamic-unl/Design.md`.
- Upstream rippled `master`, fetched 2026-11-21:
  `src/xrpld/app/misc/detail/ValidatorList.cpp` (80% quorum, lines 1765, 1800).
- Live testnet validator list: https://postfiat.org/testnet_vl.json
  (fetched 2026-11-20; re-verified byte-identical 2026-11-21).
- xrpl.org peer-protocol and consensus-protocol docs (accessed 2026-11-21).

Full source list with file:line pins: `docs/SOURCES.md`.
