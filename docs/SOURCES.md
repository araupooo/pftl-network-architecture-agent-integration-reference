# Pinned Sources

Every source this reference rests on, with the access date and the
exact pin (commit, file:line, or URL). Local code pins are against the
postfiatd checkout at commit `0085a1ff` (2026-10-10). Upstream pins are
against rippled `master` as fetched 2026-11-21. Web pages were accessed
2026-11-21 unless noted.

Verify an excerpt in the public repository with the blob pattern
(replace `<commit>` with the repository's HEAD commit after upload):

```
https://github.com/araupooo/pftl-network-architecture-agent-integration-reference/blob/<commit>/path/to/file#Lx-Ly
```

## Local code — postfiatd `0085a1ff`

| # | Path | Lines | What it pins |
|---|---|---|---|
| L1 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1898–1901 | 67% quorum comment (verbatim in `docs/NETWORK_ARCHITECTURE.md` §1) |
| L2 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1934 | Quorum formula `max(ceil(effective*0.67), ceil(unl*0.6))` |
| L3 | `src/xrpld/app/misc/detail/ValidatorList.cpp` | 1853, 1861–1886, 2109 | `--quorum` override warning; quorum disabled when publishers unavailable; `quorum_ = calculateQuorum(...)` |
| L4 | `src/xrpld/app/misc/ValidatorList.h` | 131–170, 233 | Trusted-list rules; 125% of quorum cap |
| L5 | `src/xrpld/app/misc/ValidatorSite.h` | 42–45, 65, 109 | List fetching; `refreshInterval` in minutes |
| L6 | `src/xrpld/app/misc/Manifest.h` | 279–284 | `defaultMaxUntrustedManifests = 1000`; evict-oldest; listed keys never bounded |
| L7 | `src/xrpld/overlay/detail/Tuning.h` | 32–58 | `convergedLedgerLimit` 24; `divergedLedgerLimit` 128; reply caps 8192/12288; send-queue 192/128; `checkIdlePeers` 4 s |
| L8 | `src/xrpld/overlay/detail/OverlayImpl.cpp` | 401, 648, 733 | "Over resource limit"; manifest batch limit charge; invalid/excess manifests charge |
| L9 | `src/xrpld/overlay/detail/PeerImp.cpp` | 401 | `postfiatd-` version-string prefix strip |
| L10 | `src/xrpld/overlay/Squelch.h` | 36 | "Maintains squelching of relaying messages from validators" |
| L11 | `src/xrpld/overlay/ReduceRelayCommon.h` | 38–41 | Squelch bounds 300 s / 600 s / 3600 s; `SQUELCH_PER_PEER` 10 s |
| L12 | `src/xrpld/overlay/Slot.h` | 215–217 | Squelch duration formula |
| L13 | `src/xrpld/peerfinder/detail/Tuning.h` | 40–61, 79–81 | `defaultMaxPeers` 21; `outPercent` 15; `minOutCount` 10; `maxConnectAttempts` 20; `secondsPerConnect` 10; `maxRedirects` 30; Fibonacci backoff |
| L14 | `src/xrpld/peerfinder/detail/PeerfinderConfig.cpp` | 41, 103–110 | Outbound-peer calculation → 10 outbound / 11 inbound |
| L15 | `src/xrpld/core/Config.h` | 184 | `[overlay] max_untrusted_count` config key |
| L16 | `src/xrpld/core/detail/Config.cpp` | 858–865 | `max_untrusted_count` parsing |
| L17 | `include/xrpl/protocol/SystemParameters.h` | 83–88 | Amendment threshold 67/100; two-week majority hold |
| L18 | `src/test/core/Config_test.cpp` | 105, 1116–1196 | Default hub list `r.ripple.com`, `s1.ripple.com`, `s2.ripple.com` on 51235 (test-code evidence) |
| L19 | `docs/MANIFEST_FLOOD_HOTFIX.md` | whole doc | Manifest-flood incident, 1.0.5/1.0.6, all bounds |
| L20 | `docs/NodeSetup.md` | 114–122 | Canonical testnet list URL, publisher key, threshold 0 |
| L21 | `docs/dynamic-unl/Design.md` | 3, 136–196 | Three phases; local inference; two-layer proof; 7B–32B models |
| L22 | `docs/dynamic-unl/ImplementationPlan.md` | whole doc | ~17–23 weeks; `dynamic-unl-scoring`, `validator-scoring-sidecar` |
| L23 | `docs/Architecture.md` | 68–70, 127–131 | Overlay/peerfinder roles; failure table |

Two blob-link patterns apply, and they point at different repositories:

- **This reference's own files** (scripts, docs, data, outputs) — verify
  in the reference repository after upload, substituting the real HEAD
  commit for `<commit>`:
  `https://github.com/araupooo/pftl-network-architecture-agent-integration-reference/blob/<commit>/scripts/quorum_list.py`
- **postfiatd source excerpts** (L1–L23 above) — the postfiatd source
  files themselves are not vendored in this reference; verify them
  against the postfiatd repository at commit `0085a1ff`, e.g.:
  `https://github.com/postfiatorg/postfiatd/blob/0085a1ff885d6a446369cf73a4430f75af22be55/src/xrpld/app/misc/detail/ValidatorList.cpp#L1898-L1901`

## Upstream — rippled `master` (fetched 2026-11-21)

| # | URL | Lines | What it pins |
|---|---|---|---|
| U1 | https://raw.githubusercontent.com/ripple/rippled/master/src/xrpld/app/misc/detail/ValidatorList.cpp | 1765 | 80% quorum comment |
| U2 | same file | 1786 | 80% allows < 0.2·ni unique validators |
| U3 | same file | 1800 | Formula `max(ceil(effective*0.8), ceil(unl*0.6))` |

## Live data

| # | URL | Accessed | What it pins |
|---|---|---|---|
| D1 | https://postfiat.org/testnet_vl.json | fetched 2026-11-20; re-verified byte-identical 2026-11-21 | Testnet validator list: publisher `ED3F…09E2`, sequence 30, effective 2026-11-17T20:10:08Z, expiration 2028-03-31T16:14:53Z, 25 validators (vendored as `data/testnet_vl.json`) |
| D2 | https://tasknode.postfiat.org/ | 2026-11-20 | Public page renders only "What are you working on?" — no docs, no API reference (basis for the contract being a proposal) |

## Web documentation (accessed 2026-11-21)

| # | URL | What it pins |
|---|---|---|
| W1 | https://xrpl.org/docs/concepts/networks-and-servers/peer-protocol | Peer protocol: HTTPS upgrade to `XRPL/2.0` (was `RTXP/1.2`); port 2459 / legacy 51235; gossip discovery; hardcoded hubs; node key pair; fixed peers vs reservations; private peers; peer crawler |
| W2 | https://xrpl.org/docs/concepts/consensus-protocol/ | "Fails to make progress rather than diverging"; <20% faulty → progress; >80% colluding → invalid confirmation |
| W3 | https://xrpl.org/docs/concepts/consensus-protocol/negative-unl | Default UNL 35 validators (as of 2024-06-25); quorum floor 60%; listings capped at 25% |
| W4 | https://xrpl.org/docs/concepts/networks-and-servers/amendments | Amendment voting around flag ledgers; 256-ledger reliability window |
| W5 | https://xrpl.org/configure-the-peer-crawler.html | `[crawl]` stanza fields `overlay`, `server`, `counts`, `unl` |
| W6 | https://xrpl.org/docs/references/http-websocket-apis/admin-api-methods/peer-management-methods/peers/ | `peers` admin method (per-peer address, latency, ledger, load, sanity) |

## Academic

| # | Source | What it pins |
|---|---|---|
| A1 | Chase & MacBrough, "Analysis of the XRP Ledger Consensus Protocol", arXiv:1802.07242, https://arxiv.org/pdf/1802.07242 | Theorem 8 fork-safety condition `Oi,j > nj/2 + ni − qi + ti,j` |

## Incident reporting (Feb 2025 halt; secondary reporting where noted)

| # | Source | Accessed | What it pins |
|---|---|---|---|
| I1 | CoinDesk, "XRP Ledger self-healed after brief downtime", https://www.coindesk.com/markets/2025/02/05/xrp-ledger-self-healed-after-brief-downtime | 2026-11-20 | 64-minute halt; freeze height 93,927,173; Schwartz "silent network" quote |
| I2 | Decrypt, https://decrypt.co/304451/xrp-ledger-temporarily-halts-block-production-ripple-cto | 2026-11-20 | Same incident; "validations were not being published" |
| I3 | CoinTelegraph via TradingView, https://www.tradingview.com/news/cointelegraph%3A9aae0d667094b%3A0-ripple-says-xrp-ledger-back-online-after-hourlong-network-halt/ | 2026-11-20 | Resumed ~10:58 UTC 4 Feb 2025 |
| I4 | The Block via TradingView, https://www.tradingview.com/news/the_block:1138f4c34094b:0-xrp-ledger-s-hour-long-halt-sparks-debate-over-consensus-tradeoffs/ | 2026-11-20 | ~88,000 transactions delayed (XRPSCAN); Nov 2024 node crash (~10 min, reported); Sep 2024 SQLite full-history failures (reported) |
| I5 | BeInCrypto via TradingView, https://www.tradingview.com/news/beincrypto:c5502eca0094b:0-xrp-ledger-experiences-temporary-outage-restored-after-64-minute-halt/ | 2026-11-20 | 64-minute halt; all 35 validators proposing; "only one validator operator manually intervened" |

## What could NOT be verified

- **Agent-integration specification:** no public documentation exists
  (D2). The contract in `docs/AGENT_INTEGRATION_CONTRACT.md` is a
  labelled proposal derived from the observable flow.
- **Upstream comparison:** done against current upstream `master`
  (2026-11-21), not the exact fork point. The 80% figure is confirmed
  in current master; phrase the divergence as "postfiatd 67% vs
  upstream-master 80%", not "vs the fork point".
- **Nov 2024 node crash and Sep 2024 SQLite failures:** secondary
  roundup reporting only (I4); root causes not established in the
  sources consulted. Labelled as reported.
- **Dynamic UNL status:** the design/plan docs describe intent and
  phases; whether Phase 1 is live on testnet was not verified. The
  live list (§6 of the architecture doc) is consistent with Phase 1
  and with no phase at all.
- **Hardcoded hub hostnames:** asserted in test code (L18), not in a
  doc; treated as config-default evidence.
