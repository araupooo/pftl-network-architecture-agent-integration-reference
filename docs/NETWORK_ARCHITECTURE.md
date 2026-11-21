# PFTL Network Architecture

A reference for the peer-to-peer network, consensus quorum, validator
list, and overlay behaviour of PFTL (the postfiatd fork of rippled),
pinned to postfiatd commit `0085a1ff` (2026-10-10) and upstream rippled
`master` as fetched 2026-11-21. Every substantive claim is labelled
[FAKTA] / [ESTIMASI] / [ANALISIS]. The runnable checks behind this
document are `scripts/quorum_list.py` (N-01), `scripts/peer_network_model.py`
(N-02), `scripts/unl_overlap.py` (N-03), `scripts/manifest_flood.py` (N-04),
`scripts/silent_network.py` (N-05), and `scripts/partition_drill.py` (N-06).

## 1. The 67% validator-list quorum — the headline finding

[FAKTA] `ValidatorList::calculateQuorum` in postfiatd uses a 67%
quorum, not upstream's 80%. `src/xrpld/app/misc/detail/ValidatorList.cpp:1898-1901`
(verified by `grep` on the `0085a1ff` checkout):

> "Use a 67% quorum to balance fork safety, liveness, and required UNL
> overlap. Note: Original XRPL uses 80%, but this fork uses 67% for
> devnet/testnet. For mainnet, this should be reverted to 80%."

[FAKTA] The formula, `ValidatorList.cpp:1934`:

```cpp
return static_cast<std::size_t>(std::max(
    std::ceil(effectiveUnlSize * 0.67f), std::ceil(unlSize * 0.6f)));
```

[FAKTA] Upstream rippled `master`, fetched 2026-11-21,
`src/xrpld/app/misc/detail/ValidatorList.cpp:1765`: "Use an 80% quorum
to balance fork safety, liveness, and required UNL overlap." Formula,
line 1800: `max(ceil(effectiveUnlSize * 0.8), ceil(unlSize * 0.6))`.

[FAKTA] The 60% term is the Negative UNL absolute-minimum quorum:
the comment at `ValidatorList.cpp:1930-1932` states "the effective
quorum should not be lower than it". The quorum is recomputed on every
list update (`ValidatorList.cpp:2109`:
`quorum_ = calculateQuorum(unlSize, effectiveUnlSize, seenSize)`), and a
`--quorum` command-line override is honoured with a warning
("Using potentially unsafe quorum…", line 1853). If too many
publishers are unavailable, quorum is disabled (lines 1861-1886).

[FAKTA] This is a second, distinct 67% divergence from the amendment
threshold (67/100 in `include/xrpl/protocol/SystemParameters.h:85`,
`postFixAmendmentMajorityCalcThreshold`). The quorum comment itself
says the 67% value should be reverted for mainnet — there is no
recorded proposal, review, or test in the checkout that justifies
carrying it forward. [ANALISIS] Any mainnet plan that inherits this
value without a deliberate decision is carrying a devnet/testnet
tuning knob into production by accident.

### 1.1 Re-derived quorum numbers (N-01)

[FAKTA] Recomputed by `scripts/quorum_list.py` from the two formulas
(`outputs/quorum_list.log`):

| UNL size N | postfiatd 67% | upstream 80% | offline tolerated (67% / 80%) |
|---:|---:|---:|---:|
| 25 (live testnet) | 17 | 20 | 8 / 5 |
| 35 (XRPL default UNL) | 24 | 28 | 11 / 7 |
| 100 | 67 | 80 | 33 / 20 |
| 200 | 134 | 160 | 66 / 40 |

[FAKTA] The 67% rule is strictly lower than the 80% rule for every
N ≥ 4 except N = 5 and N = 6, where ceiling rounding makes them equal
(N = 5: both 4; N = 6: both 5). The 60% floor binds for small UNLs
(at N = 2 the quorum is 2 under both rules). Neither rule ever drops
below 60% of the UNL size for N = 1..200.

[ANALISIS] The practical meaning at the live testnet size: the 67%
rule tolerates 8 of 25 validators going dark and still reaching
quorum, where the 80% rule tolerates 5. That is liveness bought with
fork-safety margin — see §3.

### 1.2 Trusted-list size

[FAKTA] `src/xrpld/app/misc/ValidatorList.h:170`: "Otherwise, the
trusted list size is set to 125% of the quorum." With a single list
all listed keys are trusted; with multiple lists the trusted set is
capped at 125% of quorum. At N = 25 under the 67% rule that cap is
ceil(17 × 1.25) = 22 (multi-list rule; the live testnet list is a
single list, so all 25 are trusted — see §6).

## 2. Peer protocol and overlay

### 2.1 How servers connect

[FAKTA] Servers communicate over the peer protocol; all information
about the behaviour, progress, and connectivity of the network passes
through it (xrpl.org peer-protocol docs, accessed 2026-11-21).
Handshake: one server connects to another using HTTPS and requests an
HTTP upgrade to switch to the `XRPL/2.0` protocol (formerly `RTXP/1.2`).
IANA assigned port **2459** for the peer protocol; older servers may
use the previous port **51235**.

[FAKTA] Peer discovery is gossip: on start-up a server reconnects to
peers it previously connected to, falling back to the hardcoded public
hubs; after connecting to a peer it asks that peer for the contact
information of other servers seeking peers. The default hub list is
asserted in test code, `src/test/core/Config_test.cpp:105,1116-1196`:
`r.ripple.com 51235`, `s1.ripple.com 51235`, `s2.ripple.com 51235`
(test code asserting config defaults — config-default evidence, not a
doc statement).

[FAKTA] Each server generates a node key pair on first start-up to
identify itself in peer communications and signs all its peer
communications with it; the key is saved in the database and reused
across restarts, and a `[node_seed]` stanza pins it.

[FAKTA] Fixed peers (`[ips_fixed]`) vs peer reservations: a server
with a peer reservation for a specific peer always accepts connection
requests from that peer even at its maximum peer count (which can push
it over the maximum). Reservations are keyed by node key pair and
adjustable while online; fixed peers need a restart.

[FAKTA] Private peers: a private server does not make outgoing
connections or accept incoming connections unless explicitly
configured, and asks its direct peers not to reveal its IP address.
Validators always ask their peers to hide the validators' IP
addresses, regardless of the private-server settings.

[FAKTA] The peer crawler API is public by default: servers provide
statistics to anyone who asks, to make it easier to track the health
and topology of the network. The `[crawl]` stanza controls the
`overlay`, `server`, `counts`, and `unl` fields. This is the public
topology data source for the network.

### 2.2 Pinned tuning constants (N-02)

[FAKTA] Peerfinder, `src/xrpld/peerfinder/detail/Tuning.h`
(verified by `grep`):

| Parameter | Value |
|---|---|
| `defaultMaxPeers` | 21 |
| `outPercent` | 15 |
| `minOutCount` | 10 |
| `maxConnectAttempts` | 20 |
| `secondsPerConnect` | 10 |
| `maxRedirects` | 30 |
| `connectionBackoff` | Fibonacci {1, 1, 2, 3, 5, 8, 13, 21, 34, 55} (seconds) |

[FAKTA] `src/xrpld/peerfinder/detail/PeerfinderConfig.cpp:41,103-110`:
outbound peers = the larger of `minOutCount` and
`(maxPeers * outPercent + 50) / 100`; with defaults that is
max(10, 3) = **10 outbound, 11 inbound** of 21 total. If the node
cannot accept incoming connections, outbound = maxPeers. Below
`minOutCount`, maxPeers is raised to it.

[FAKTA] Overlay, `src/xrpld/overlay/detail/Tuning.h`:

| Parameter | Value |
|---|---|
| `convergedLedgerLimit` | 24 ledgers (a server that far behind is still "converged") |
| `divergedLedgerLimit` | 128 ledgers |
| `softMaxReplyNodes` / `hardMaxReplyNodes` | 8192 / 12288 ledger entries per reply |
| `dropSendQueue` / `targetSendQueue` | 192 / 128 messages |
| `checkIdlePeers` | 4 seconds |

[FAKTA] Squelch (reduce-relay), `src/xrpld/overlay/ReduceRelayCommon.h:38-41`
and `src/xrpld/overlay/Slot.h:215-217`: a peer's squelch lasts a random
duration in [300 s, min(max(600, 10 × npeers), 3600 s)].
`src/xrpld/overlay/Squelch.h:36`: "Maintains squelching of relaying
messages from validators" — validations and proposals are not relayed
to squelched peers, which bounds gossip amplification.

[FAKTA] Resource accounting: `src/libxrpl/resource/ResourceManager.cpp`
does per-peer accounting; `src/xrpld/overlay/detail/OverlayImpl.cpp:401`
logs "Over resource limit" on disconnect, and line 648 charges the
sender (`Resource::feeInvalidData`, "manifest batch limit") for
oversized manifest batches — the manifest-flood defence in the overlay
itself.

[FAKTA] The only postfiatd-specific change in the overlay/peerfinder
code is version-string branding: `src/xrpld/overlay/detail/PeerImp.cpp:401`,
`getVersion()` strips a `"postfiatd-"` prefix from the peer's
`User-Agent`/`Server` header. No other `PF_`/`PFTL`/`postfiat` hit
exists in `src/xrpld/overlay` or `src/xrpld/peerfinder`.

### 2.3 Deterministic gossip model (N-02)

[ANALISIS] The model in `scripts/peer_network_model.py` is a model of
the documented parameters, not a measurement of the live network: it
answers "what do these parameters imply", not "what does the network
do". N nodes, each holding up to 21 peer slots (10 outbound, 11
inbound), gossip a validation round by round (1 s per round) with a
fixed seed (`20261120`). Measured in `outputs/peer_network_model.log`:

- [FAKTA] Topology (N = 25, live testnet size): min degree 10, max
  degree ≤ 21, single connected component.
- [FAKTA] A validation injected at any single validator reaches all
  25 validators within the 5 s upper bound of the 3–5 s ledger cadence.
- [FAKTA] With 5 squelched relays, full propagation still completes.
- [FAKTA] With 4 validators dropped (reconnecting per the Fibonacci
  backoff), 21 validators remain alive — above the 17 quorum.

## 3. UNL overlap and fork safety

[FAKTA] Theorem 8 (Chase & MacBrough, arXiv:1802.07242), quoted
verbatim in both the postfiatd and upstream `calculateQuorum`
comments: fork safety holds if `Oi,j > nj/2 + ni − qi + ti,j` for every
pair of nodes. The postfiatd comment derives from it: with
qi = 0.67·ni, two UNLs may safely have < 0.33·ni unique validators
between them; with qi = 0.8·ni, < 0.2·ni.

[FAKTA] The overlap map (`scripts/unl_overlap.py`,
`outputs/unl_overlap.log`), two UNLs of size 25 with p unique
validators each side (overlap O = 25 − p, pi + pj = 2p):

| Overlap O/25 | Fork-safe under 67%? | Fork-safe under 80%? |
|---:|---:|---:|
| 25 (identical) | yes | yes |
| 23 | yes | yes (2p = 4 < 5.0) |
| 22 | yes (2p = 6 < 8.25) | **no** (6 > 5.0) |
| 21 | yes (2p = 8 < 8.25) | no |
| 20 | **no** (2p = 10 > 8.25) | no |

[FAKTA] The minimum fork-safe overlap is 21 of 25 under the 67% rule
and 23 of 25 under the 80% rule: the 67% rule admits 2 more unique
validators per side (4 vs 2).

[FAKTA] Reference design numbers (XRPL, not PFTL's live set): the
default UNL has 35 validators; the network has 200+ validators in
total, with a much smaller number on UNLs. The worst-case minimum
overlap bound from Chase & MacBrough is roughly >90% of the UNL.

[FAKTA] Partition behaviour (xrpl.org consensus docs, accessed
2026-11-21): "If too many participants are unreachable or misbehaving,
the network fails to make progress rather than diverging or confirming
invalid transactions." "As long as fewer than 20% of trusted
validators are faulty, consensus can continue unimpeded; and confirming
an invalid transaction would require over 80% of trusted validators to
collude." Negative UNL: quorum floor 60% of total; listings capped at
25% of UNL; more than 20% offline stops validation.

## 4. Manifest-flood hotfix (1.0.5 / 1.0.6)

[FAKTA] `docs/MANIFEST_FLOOD_HOTFIX.md` documents a network-ingress
flood of validator manifests (unlisted keys) on testnet/devnet.
Version 1.0.5 closed the flood by refusing every manifest whose master
key is not on the validator list — which also blocked learning about
not-yet-listed validators, breaking the dynamic UNL flow. Version
1.0.6 follows XRPL's 3.3.0 corrected design with one deliberate
difference: "XRP Ledger rejects new unlisted keys once its bound is
full, while 1.0.6 evicts the oldest unlisted entry instead, so a flood
churns the set but can never leave the node blind to a newcomer until
the next restart."

[FAKTA] The bounds, verified in code as well as the hotfix doc:

| Parameter | Value | Source |
|---|---|---|
| Unlisted-manifest bound | 1000 keys (default) | `docs/MANIFEST_FLOOD_HOTFIX.md`; `src/xrpld/app/misc/Manifest.h:279-284` (`defaultMaxUntrustedManifests = 1000`), override `[overlay] max_untrusted_count` |
| Per-manifest cap | 512 bytes (was 4 KiB) | hotfix doc; `Manifest.h` |
| Legacy drain | one oversized 1.0.4 dump up to 256 MiB − 1 within 300 s (was 128 MiB / 60 s) | hotfix doc |
| Incoming batch cap | 500 entries and 512 KiB | hotfix doc |
| Unlisted manifests in `wallet.db` | never written | hotfix doc |
| Listed keys | never bounded or evicted | hotfix doc; `Manifest.h:281` |
| Greeting | every listed manifest plus a random subset of at most `max_untrusted_count` unlisted ones | hotfix doc |
| Revocations of unlisted keys | never sent | hotfix doc |

[FAKTA] The replay in `scripts/manifest_flood.py`
(`outputs/manifest_flood.log`) floods 2500 unlisted keys against the
1000-key bound under both policies:

- [FAKTA] Reject-when-full (XRPL 3.3.0): the set never exceeds 1000
  keys, but a newcomer arriving mid-flood is refused once the set is
  full and stays undiscovered.
- [FAKTA] Evict-oldest (postfiatd 1.0.6): the newcomer is admitted
  mid-flood (evicting the oldest entry), but is churned out by the
  next 1000 flood arrivals — discovery at arrival is preserved,
  discovery durability under a sustained flood is not.

[ANALISIS] Manifest handling is the overlay's largest unauthenticated
ingress surface. The bound/eviction policy is a tunable that trades
flood resistance against newcomer discovery: reject-when-full fails
closed on discovery, evict-oldest fails open on durability. An
operator choosing `max_untrusted_count` below the number of validators
the network may be asked to score (`Manifest.h:279-284` warns it "must
stay well above" that number) reintroduces the 1.0.5 blindness by
configuration.

## 5. Dynamic UNL

[FAKTA] `docs/dynamic-unl/Design.md`: validators progressively take
over UNL scoring from the foundation in three phases — "foundation
scores alone (Phase 1), validators verify the foundation's work
(Phase 2), validators prove they did the work honestly (Phase 3). By
Phase 3, the foundation is no longer the authority — validators
collectively determine the UNL."

[FAKTA] Design decisions (same doc): local inference on open-weight
models (no cloud API); one mandatory GPU type for all scorers
("Guarantees determinism"); two-layer proof — output convergence +
proof-of-logits; data published to IPFS with the CID on-chain; scoring
carries no direct payment ("XRPL model"); one-time validator grants.
Model pinning via a full execution manifest (weights hashes,
tokenizer, prompt template version, SGLang version, dtype,
quantization, container digest, CUDA/driver). Target model class
7B–32B parameters. Data sources: VHS API (agreement, uptime, latency,
peer connections, server version, manifests, amendment voting, fee
votes, domain verification), ASN/WHOIS, MaxMind GeoIP2 (not
republished — EULA), on-chain identity records.

[FAKTA] Implementation plan (`docs/dynamic-unl/ImplementationPlan.md`):
~17–23 weeks total (Phase 0 ~1 wk, Phase 1 ~4–6 wks, Phase 2 ~6–8 wks,
Phase 3 ~5–7 wks); repos `dynamic-unl-scoring` (Python/FastAPI) and
`validator-scoring-sidecar` (Python, GPU sidecar).

[FAKTA] The canonical testnet list is
`https://postfiat.org/testnet_vl.json`, publisher key
`ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2`,
threshold 0 (`docs/NodeSetup.md:114-122`). "The Dynamic UNL scoring
service updates the signed list behind that canonical URL on a periodic
basis."

[ANALISIS] The design and plan docs describe intent and phases;
whether Phase 1 is live on testnet was not verified in this reference.
The live list in §6 is the observable state: a single foundation-signed
list, which is consistent with Phase 1 (foundation scores alone) and
with no phase at all. Do not cite this reference as proof that dynamic
UNL is operational.

## 6. Worked audit: the live testnet validator list

[FAKTA] The live list was fetched from
`https://postfiat.org/testnet_vl.json` on 2026-11-20, vendored as
`data/testnet_vl.json`, and re-verified byte-identical against the live
URL on 2026-11-21. Checks in `scripts/unl_overlap.py`
(`outputs/unl_overlap.log`):

| Field | Value |
|---|---|
| Publisher key | `ED3F1E0DA736FCF99BE2880A60DBD470715C0E04DD793FB862236B070571FC09E2` — matches the documented key in `docs/NodeSetup.md:114-122` |
| List version | 2 (`blobs_v2`) |
| Sequence | 30 |
| Effective | 2026-11-17T20:10:08Z |
| Expiration | 2028-03-31T16:14:53Z |
| Validators | 25, all with manifests, all keys distinct, all ED-prefixed hex |
| Manifest sizes | 225–246 bytes each — every one under the 512-byte cap (§4) |
| Quorum at N = 25 | 17 under the 67% rule; 20 under the 80% rule |

[FAKTA] The list is a single list, so under `ValidatorList.h:131-170`
all 25 listed keys are trusted, and the 125%-of-quorum cap (22) does
not apply. The list was effective at the 2026-11-21 reference date
(effective < 2026-11-21 < expiration).

### 6.1 Validator overlay table

[FAKTA] All 25 validators from the vendored list, in list order.
Keys are shown truncated (first 16 + last 6 hex chars); the full keys
are in `data/testnet_vl.json`. Manifest sizes are decoded byte lengths
of the base64 manifests.

| # | Validation public key | Manifest |
|---:|---|---:|
| 1 | ED4D4244B734459A…470A59 | 225 B |
| 2 | ED154DB8240191EE…B75C3D | 237 B |
| 3 | ED50A48CC2489D0B…A803CB | 240 B |
| 4 | EDE8F9E784C5889B…F6611B | 246 B |
| 5 | ED921B111B30DE15…B7D974 | 238 B |
| 6 | EDA76CF43ED17F57…08BC7D | 231 B |
| 7 | ED2DB2949D5B3994…609982 | 243 B |
| 8 | ED004DBFCC00F23D…CF1333 | 232 B |
| 9 | ED123A54609CA70E…C93346 | 228 B |
| 10 | ED18B80CFF66576D…C28576 | 230 B |
| 11 | ED201FD47A909013…C9BB94 | 240 B |
| 12 | ED21D2377A78BAFF…65BEC1 | 229 B |
| 13 | ED4F62A8245E10D8…79B3AF | 229 B |
| 14 | ED518DF35FB7DF74…7BAF54 | 236 B |
| 15 | ED9374294AB208D6…D4B6E1 | 238 B |
| 16 | ED6F750D3C7254AF…523F5D | 230 B |
| 17 | ED6B25E466E4DC2C…E45175 | 229 B |
| 18 | EDD81DA4510C650D…FA4C99 | 232 B |
| 19 | ED372A9FAC2AE88D…CCD2D6 | 233 B |
| 20 | EDE79A060F7412E5…5A4F3C | 230 B |
| 21 | EDEF0DC9039DF384…166857 | 244 B |
| 22 | EDCE5B0D1AA64FED…1A3658 | 240 B |
| 23 | ED988B2907AAFBDB…B22735 | 225 B |
| 24 | ED62AA9FB1148550…52C19B | 237 B |
| 25 | EDAC24E230EA8374…01D73F | 245 B |

[ANALISIS] What the table does and does not show: it is the signed
list as published, not a liveness or agreement measurement. It says
nothing about which of these validators are currently online, agreeing,
or reachable — those need the peer crawler, the `peers` admin method,
or the VHS API (§2.1, §3). The audit's finding is structural: a
single-publisher list of 25, quorum 17 under the live 67% rule, with
every manifest well under the flood cap. If the publisher key ever
differs from the documented one, or the sequence stops advancing, that
is the first thing this audit would flag — `scripts/unl_overlap.py`
checks the publisher key on every run.

## 7. Ledger cadence and amendment voting (context)

[FAKTA] New ledger versions close about every 3–5 seconds (xrpl.org
learning material, "How the XRP Ledger works"); flag ledgers occur
every 256 ledgers, i.e. roughly every 12–20 minutes at that cadence
(derived arithmetic). Amendment voting happens around flag ledgers;
reliability is tracked over the last 256 ledgers (~15–20 minutes).
