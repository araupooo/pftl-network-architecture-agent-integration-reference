# Claims Index

Every substantive claim in this reference, mapped to the runnable
check that tests it, the unedited log that records the result, and
the pinned primary source. Labels: [FAKTA] verified with source +
date, [ESTIMASI] modelled/reported number, [ANALISIS] interpretation.

Verify an excerpt in the reference repository at commit
`c92413c29be86a9293eac854cac83ad4d8e8ade6`:

```
https://github.com/araupooo/pftl-network-architecture-agent-integration-reference/blob/c92413c29be86a9293eac854cac83ad4d8e8ade6/scripts/quorum_list.py
https://github.com/araupooo/pftl-network-architecture-agent-integration-reference/blob/c92413c29be86a9293eac854cac83ad4d8e8ade6/docs/NETWORK_ARCHITECTURE.md
https://github.com/araupooo/pftl-network-architecture-agent-integration-reference/blob/c92413c29be86a9293eac854cac83ad4d8e8ade6/data/testnet_vl.json
```

Verify a postfiatd source excerpt against the postfiatd repository
at commit `0085a1ff`:

```
https://github.com/postfiatorg/postfiatd/blob/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/misc/detail/ValidatorList.cpp#L1898-L1901
```

## N-01 — Quorum re-derivation (`scripts/quorum_list.py`, `outputs/quorum_list.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C1 | postfiatd `calculateQuorum` uses a 67% quorum; the comment says "for devnet/testnet" and "should be reverted to 80%" for mainnet | [FAKTA] | Quorum formula re-derived for N=1..200 | `ValidatorList.cpp:1898-1901` (verbatim quote in `docs/NETWORK_ARCHITECTURE.md` §1); blob: `postfiatd/blob/0085a1ff…/src/xrpld/app/misc/detail/ValidatorList.cpp#L1898-L1901` |
| C2 | Formula is `max(ceil(effective*0.67), ceil(unl*0.6))` | [FAKTA] | Same | `ValidatorList.cpp:1934` |
| C3 | Upstream uses 80%: `max(ceil(effective*0.8), ceil(unl*0.6))` | [FAKTA] | Same | rippled `master` fetched 2026-11-21, `ValidatorList.cpp:1765,1800` |
| C4 | At N=25: quorum 17 (67%) vs 20 (80%); offline tolerance 8 vs 5 | [FAKTA] | `TESTNET` + `TOLERANCE` checks | Derived from C2/C3 by the script; log lines "live testnet UNL N=25" |
| C5 | 67% rule is strictly lower for every N ≥ 4 except N=5, N=6 (equal by ceiling rounding) | [FAKTA] | `DIVERGENCE` check | Derived from C2/C3; script asserts over N=1..200 |
| C6 | Neither rule drops below 60% of the UNL for N=1..200 | [FAKTA] | `FLOOR` checks | 60% term is the Negative UNL absolute-minimum quorum (`ValidatorList.cpp:1930-1932`) |
| C7 | 67% allows < 0.33·ni unique validators between two UNLs; 80% allows < 0.20·ni | [FAKTA] | `MARGIN` checks | Theorem 8, arXiv:1802.07242, as derived in the `ValidatorList.cpp:1902-1929` comment |
| C8 | Trusted-list size is 125% of quorum with multiple lists; all keys trusted with a single list | [FAKTA] | `TESTNET: trusted-list size` check | `ValidatorList.h:170` |
| C9 | The 67% list quorum is a second, distinct 67% divergence from the amendment threshold (67/100) | [ANALISIS] | — | Amendment threshold `SystemParameters.h:85`; quorum comment C1 |
| C10 | Carrying the 67% value to mainnet without a deliberate decision would be accidental | [ANALISIS] | — | C1 (comment itself calls for reversion); no proposal/review/test found in the checkout |

## N-02 — Peer-network model (`scripts/peer_network_model.py`, `outputs/peer_network_model.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C11 | `defaultMaxPeers` 21; `outPercent` 15; `minOutCount` 10; `maxConnectAttempts` 20; `secondsPerConnect` 10; `maxRedirects` 30; backoff Fibonacci {1,1,2,3,5,8,13,21,34,55} | [FAKTA] | Constants printed in the log header | Peerfinder `detail/Tuning.h:40-61,79-81` |
| C12 | Outbound = max(10, 3) = 10; 10 outbound / 11 inbound of 21 at defaults | [FAKTA] | `TOPOLOGY` checks | `PeerfinderConfig.cpp:41,103-110` |
| C13 | Overlay: converged 24 / diverged 128 ledgers; reply caps 8192/12288; send-queue drop 192 / target 128; idle-peer check 4 s | [FAKTA] | `QUEUE` check | Overlay `detail/Tuning.h:32-58` |
| C14 | Squelch duration in [300 s, min(max(600, 10·npeers), 3600 s)] | [FAKTA] | Constants in the log header | `ReduceRelayCommon.h:38-41`; `Slot.h:215-217` |
| C15 | A validation reaches all 25 validators within the 5 s ledger-cadence bound, from any source, and with 5 squelched relays | [FAKTA] | `PROPAGATION` + `SQUELCH` checks | Model output; parameters from C11–C14; cadence 3–5 s (xrpl.org) |
| C16 | 4 validators dropped: 21 remain alive, above the 17 quorum | [FAKTA] | `CHURN` checks | Model output; quorum from C4 |
| C17 | The model answers "what do these parameters imply", not "what does the network do" | [ANALISIS] | — | Method note in `docs/NETWORK_ARCHITECTURE.md` §2.3 |

## N-03 — UNL overlap (`scripts/unl_overlap.py`, `outputs/unl_overlap.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C18 | Live testnet list: publisher `ED3F…09E2` matches the documented key; sequence 30; 25 validators, all with manifests, all keys distinct and ED-prefixed | [FAKTA] | `VL` checks | `data/testnet_vl.json` (fetched 2026-11-20, re-verified byte-identical 2026-11-21); `docs/NodeSetup.md:114-122` |
| C19 | List effective 2026-11-17T20:10:08Z, expiration 2028-03-31T16:14:53Z; effective at the 2026-11-21 reference date | [FAKTA] | `VL: list is effective` check | `data/testnet_vl.json` (Ripple-epoch seconds decoded in the script) |
| C20 | Minimum fork-safe overlap: 21/25 under 67%, 23/25 under 80%; O=22 is safe under 67% but not under 80% | [FAKTA] | `OVERLAP` checks | Theorem 8 (C7); script map over O=25,23,22,21,20,18 |
| C21 | XRPL default UNL is 35 validators; 200+ validators network-wide | [FAKTA] | — | xrpl.org Negative UNL docs (W3); The Block via TradingView, Feb 2025 (I4) |
| C22 | The XRPL 35-validator set is the reference design, not PFTL's live set | [ANALISIS] | — | C18 vs C21 |

## N-04 — Manifest flood (`scripts/manifest_flood.py`, `outputs/manifest_flood.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C23 | 1.0.5 refused all unlisted manifests, blocking newcomer discovery; 1.0.6 evicts oldest instead of rejecting when full | [FAKTA] | `DISCOVERY` checks | `docs/MANIFEST_FLOOD_HOTFIX.md`; `Manifest.h:279-284` |
| C24 | Bound 1000 keys (`[overlay] max_untrusted_count`); per-manifest cap 512 B (was 4 KiB); legacy drain 256 MiB − 1 / 300 s (was 128 MiB / 60 s) | [FAKTA] | `CAP` + `DRAIN` checks | Hotfix doc; `Manifest.h:279-284` (`defaultMaxUntrustedManifests = 1000`); `Config.h:184`; `Config.cpp:858-865` |
| C25 | Reject-when-full: newcomer refused once full, stays undiscovered. Evict-oldest: newcomer admitted mid-flood, churned out by the next 1000 arrivals | [FAKTA] | `FLOOD` + `DISCOVERY` checks | Replay output; hotfix doc quote in `docs/NETWORK_ARCHITECTURE.md` §4 |
| C26 | Listed keys are never bounded or evicted | [FAKTA] | `LISTED` check | Hotfix doc; `Manifest.h:281` |
| C27 | Manifest handling is the overlay's largest unauthenticated ingress surface; the bound/eviction policy trades flood resistance against newcomer discovery | [ANALISIS] | — | C23–C26 |

## N-05 — Silent network (`scripts/silent_network.py`, `outputs/silent_network.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C28 | 4 Feb 2025: network froze at height 93,927,173/174 for 64 minutes; resumed ~10:58 UTC; ~88,000 transactions delayed; all 35 validators proposing; "only one validator operator manually intervened" | [FAKTA] | `INCIDENT` checks | CoinDesk (I1), Decrypt (I2), CoinTelegraph (I3), The Block (I4), BeInCrypto (I5) — reported figures, used as test inputs |
| C29 | "It looked like consensus was running but validations were not being published" — D. Schwartz | [FAKTA] | — | I1/I2 (direct quote) |
| C30 | Detector: 3 consecutive zero-validation ledgers while consensus advances → flag at the first zero ledger; 1–2 ledgers → no flag; 0 validations with consensus not advancing → different failure class | [FAKTA] | `HEALTHY`, `BLIP`, `GAP-2`, `GAP-3`, `STALLED` checks | Detector definition in the script; incident shape from C28 |
| C31 | 64 min at 3–5 s cadence = 768–1280 ledgers with 0 validations | [FAKTA] | `INCIDENT` arithmetic checks | Derived arithmetic from C28 + ledger cadence (xrpl.org) |
| C32 | Validation publication is a separate liveness signal from consensus running | [ANALISIS] | — | C29–C31 |

## N-06 — Partition drill (`scripts/partition_drill.py`, `outputs/partition_drill.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C33 | "If too many participants are unreachable or misbehaving, the network fails to make progress rather than diverging or confirming invalid transactions" | [FAKTA] | — | xrpl.org consensus docs (W2) |
| C34 | <20% faulty → progress continues; >80% colluding → invalid confirmation possible | [FAKTA] | `PARTITION` collusion checks | W2 |
| C35 | At N=25: 6 offline → progress under 67%, halt under 80%; 9 offline → halt under both; 13/12 split → both sides halt, no divergent ledger | [FAKTA] | `PARTITION` + `SPLIT` checks | Drill output; quorum from C4; rule from C33 |
| C36 | 20 of 25 colluding (80%) → invalid confirmation possible; 19 (76%) → not enough | [FAKTA] | `PARTITION` collusion checks | W2 (C34) |

## N-07 — Contract conformance (`scripts/contract_conformance.py`, `outputs/contract_conformance.log`)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C37 | The platform's public page renders only "What are you working on?" — no docs, no API reference, no public repository found | [FAKTA] | — | https://tasknode.postfiat.org/ fetched 2026-11-20 (D2) |
| C38 | The contract is a proposal derived from the observable flow, not a specification | [ANALISIS] | — | C37 |
| C39 | Observed flow: Offered → Accepted → Submitted → verification requested → verification response → settlement outcome | [FAKTA] | `POSITIVE` checks | Observed flow, recorded 2026-11-20 (research report §4) |
| C40 | Evidence types observed: URL, commit, text | [FAKTA] | `POSITIVE` evidence-kinds check | Same |
| C41 | Settlement outcomes carry value, completion score, evidence score, transaction hash, CID | [FAKTA] | `POSITIVE` five-fields check | Same |
| C42 | The proposed rules (R1–R5) hold on the observed flow and reject six malformed sequences | [FAKTA] | `POSITIVE` + six `NEGATIVE` checks | Harness output |
| C43 | A submitted task with no platform message is flagged as awaiting a response, never assumed settled | [ANALISIS] | `LIVENESS` check | Harness output; rule stated in `docs/AGENT_INTEGRATION_CONTRACT.md` §3 |

## Worked audit — live testnet list (`docs/NETWORK_ARCHITECTURE.md` §6)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C44 | Overlay table: 25 validators, manifest sizes 225–246 B, all under the 512 B cap | [FAKTA] | `VL` checks in N-03 | `data/testnet_vl.json`; cap from C24 |
| C45 | Single list → all 25 keys trusted; the 125%-of-quorum cap (22) does not apply | [FAKTA] | — | `ValidatorList.h:131-170` (C8) |
| C46 | The table is the signed list as published, not a liveness or agreement measurement | [ANALISIS] | — | C18–C19; liveness needs the peer crawler / `peers` method / VHS API |

## Dynamic UNL (`docs/NETWORK_ARCHITECTURE.md` §5)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C47 | Three phases: foundation scores alone → validators verify → validators prove honesty; by Phase 3 "the foundation is no longer the authority" | [FAKTA] | — | `docs/dynamic-unl/Design.md:3` |
| C48 | Local inference on open-weight models; one mandatory GPU type; two-layer proof (output convergence + proof-of-logits); IPFS publication with CID on-chain; 7B–32B models | [FAKTA] | — | `Design.md` |
| C49 | Implementation plan ~17–23 weeks; repos `dynamic-unl-scoring`, `validator-scoring-sidecar` | [FAKTA] | — | `ImplementationPlan.md` |
| C50 | Whether Phase 1 is live on testnet was not verified; the live list is consistent with Phase 1 and with no phase at all | [ANALISIS] | — | C18–C19 vs C47 |

## Peer protocol (`docs/NETWORK_ARCHITECTURE.md` §2.1)

| # | Claim | Label | Check | Pinned source |
|---|---|---|---|---|
| C51 | Handshake: HTTPS upgrade to `XRPL/2.0` (was `RTXP/1.2`); port 2459, legacy 51235; gossip discovery; hardcoded hubs | [FAKTA] | — | xrpl.org peer-protocol docs (W1), re-verified 2026-11-21 |
| C52 | Node key pair generated on first start-up, signs all peer communications, reused across restarts, pinnable via `[node_seed]` | [FAKTA] | — | W1 |
| C53 | Fixed peers vs reservations; private peers; validators always hide their IPs; peer crawler public by default | [FAKTA] | — | W1; `[crawl]` stanza (W5) |
| C54 | Default hubs `r.ripple.com`, `s1.ripple.com`, `s2.ripple.com` on 51235 are asserted in test code, not a doc | [FAKTA] | — | `Config_test.cpp:105,1116-1196` (L18) |
| C55 | The only postfiatd-specific overlay/peerfinder change is the `postfiatd-` version-string strip | [FAKTA] | — | `PeerImp.cpp:401` (L9); grep of `src/xrpld/overlay`, `src/xrpld/peerfinder` |
