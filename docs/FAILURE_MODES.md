# Failure-Mode Catalogue

Documented network incidents and the failure modes they demonstrate,
with what each implies for an operator of a PFTL node. Sources are
pinned in `docs/SOURCES.md`; every claim below is labelled
[FAKTA] / [ESTIMASI] / [ANALISIS]. The detectors and drills for the
modelled modes are `scripts/silent_network.py` (N-05),
`scripts/partition_drill.py` (N-06), and `scripts/manifest_flood.py`
(N-04).

## F-01. Silent network — validations not published (XRPL, 4 Feb 2025)

[FAKTA] Network activity froze at ledger height 93,927,173/174 for
64 minutes; it resumed ~10:58 UTC 4 Feb 2025. "It looked like
consensus was running but validations were not being published,
causing the network to drift apart" (David Schwartz, Ripple CTO, via
CoinDesk/Decrypt/CoinTelegraph, 2025-02-04/05). "One possible failure
mode for XRPL is if all the validators think something's wrong with
the network, all refuse to send any validations, and then there's no
chatter to let the network reconverge. This is the 'silent network'
failure." ~88,000 transactions delayed (XRPSCAN, reported); no assets
at risk; "very few UNL validators" made changes — possibly spontaneous
recovery; "only one validator operator manually intervened" (later
updates). All 35 validators were actively proposing during the
incident.

[ANALISIS] Audit lesson: validation *publication* is a separate
liveness signal from consensus *running*. A monitor that watches only
ledger close cadence will report a healthy network while validations
have stopped. The detector in N-05 flags 3 consecutive ledgers with
0 validations while consensus rounds keep advancing; a single such
ledger is a blip, not a halt. At the 3–5 s cadence, the 64-minute halt
is 768–1280 ledgers with 0 validations — the detector fires at the
freeze height on that shape.

Operator implications: watch validations-per-ledger, not just ledger
close cadence; alert on 3 consecutive zero-validation ledgers while
rounds advance; treat "ledgers closing, validations silent" as a
distinct incident class from "ledgers stopped".

## F-02. Node crash halts processing (XRPL, Nov 2024)

[FAKTA] "In November 2024, the network temporarily halted transaction
processing for about 10 minutes due to a node crash." (TradingView /
CoinStats, Feb 2025 roundups; secondary reporting.) Cause details not
established in the sources consulted — label as reported, not
verified.

[ANALISIS] Audit lesson: a single node crash halting the network for
10 minutes points at the same quorum fragility as F-01 — a small UNL
means a few failures matter. Under the live PFTL 67% rule at N = 25,
9 validators offline (36%) halts the network (N-06); under the 80%
rule, 6 offline (24%) halts it. The 67% rule buys liveness against
exactly this class of outage.

Operator implications: with a 25-validator UNL, the network's halt
threshold is 9 simultaneous validator outages under the current
quorum; monitor the count of unreachable UNL members against that
number, not against an absolute.

## F-03. Full-history node failures (XRPL, Sep 2024)

[FAKTA] "In September 2024, full history nodes on XRPL experienced
failures caused by an SQLite database page size limitation, which led
to inefficiencies in handling large transaction data" and "required
emergency patches to resolve." (TradingView, Feb 2025 roundups;
secondary reporting.)

[ANALISIS] Audit lesson: history-serving nodes are a distinct failure
class from validators. Ledger acquisition fails when peers lack the
requested history (`docs/Architecture.md:131`: "Ledger acquisition
failure — Peers don't have the requested ledger history"), and the
reply caps in the overlay (`softMaxReplyNodes` 8192 /
`hardMaxReplyNodes` 12288) bound how much history a peer will serve
per reply. A node that cannot acquire history is not a consensus
failure, but it is a sync failure with the same user-visible symptom.

Operator implications: monitor ledger-acquisition failures separately
from consensus health; a node stuck syncing is not evidence the
network has halted.

## F-04. Manifest flood (postfiatd, 1.0.5 / 1.0.6, testnet/devnet)

[FAKTA] A flood of validator manifests from unlisted keys hit the
network. 1.0.5 closed it by refusing every manifest whose master key
is not on the validator list — which also blocked learning about
not-yet-listed validators, breaking the dynamic UNL flow. 1.0.6
follows XRPL's 3.3.0 corrected design with one deliberate difference:
evict-oldest instead of reject-when-full. Bounds: 1000 unlisted keys
(`[overlay] max_untrusted_count`), 512 bytes per manifest (was
4 KiB), legacy drain of one oversized 1.0.4 dump up to 256 MiB − 1
within 300 s (was 128 MiB / 60 s). Full detail in
`docs/NETWORK_ARCHITECTURE.md` §4.

[FAKTA] The replay (N-04) shows the two policies' failure modes
exactly: reject-when-full leaves the node blind to a newcomer that
arrives after the set fills; evict-oldest admits the newcomer but
churns it out under a sustained flood. Neither policy makes discovery
durable under flood — they fail in different directions.

Operator implications: keep `max_untrusted_count` well above the
number of validators the network may be asked to score
(`Manifest.h:279-284`); setting it to 0 restores the 1.0.5 behaviour
and blinds the node to newcomers; a sudden rise in unlisted-manifest
admissions is the early warning of a flood, before any bound is hit.

## F-05. Partition — halt, not fork

[FAKTA] Under the consensus rules, a partition removes quorum rather
than producing a divergent ledger: "If too many participants are
unreachable or misbehaving, the network fails to make progress rather
than diverging or confirming invalid transactions" (xrpl.org
consensus docs). Confirming an invalid transaction would require over
80% of trusted validators to collude.

[FAKTA] The drill (N-06) at the live testnet size (N = 25, quorum
17): 6 offline → progress under 67%, halt under 80%; 9 offline →
halt under both; a 13/12 split → both sides halt, neither side
confirms a divergent ledger; 20 of 25 colluding (80%) → invalid
confirmation becomes possible; 19 colluding (76%) → not enough.

Operator implications: the correct response to a partition is to
restore connectivity, not to restart validators or force progress —
there is no divergent ledger to reconcile, and any manual intervention
that fabricates quorum risks the one outcome the protocol is designed
never to produce.

## F-06. Peer disconnection and ledger-acquisition failure

[FAKTA] `docs/Architecture.md:127-131` lists the failure table:
"Peer disconnections — Network instability, protocol version mismatch,
or timeout"; "Ledger acquisition failure — Peers don't have the
requested ledger history". The overlay charges peers for oversized
manifest batches and disconnects peers over the resource limit
(`OverlayImpl.cpp:401,648`).

[ANALISIS] These are routine, self-healing failure modes — the
peerfinder backoff (Fibonacci 1–55 s) and the 21-peer slot budget
exist to absorb them. They become an incident only in aggregate:
many simultaneous disconnections with a common cause (a bad release,
a network event) look like F-05 from the inside, and the
distinguishing signal is whether quorum is still reachable, not how
many peers dropped.

Operator implications: alert on quorum reachability and on
validations-per-ledger (F-01), not on raw peer counts; a node with
10 outbound peers and a full inbound set is healthy even while
individual peers churn.
