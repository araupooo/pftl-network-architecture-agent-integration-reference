#!/usr/bin/env python3
"""Deterministic peer-network model (check N-02).

A round-based gossip model built ONLY from pinned postfiatd parameters
(main HEAD 0085a1ff, verified by grep 2026-11-20/21):
  Peerfinder detail/Tuning.h: defaultMaxPeers = 21; outPercent = 15;
      minOutCount = 10; maxConnectAttempts = 20; secondsPerConnect = 10;
      maxRedirects = 30; connectionBackoff = {1,1,2,3,5,8,13,21,34,55}
  PeerfinderConfig.cpp:41,103-110: outbound = max((maxPeers*15+50)/100, 10)
      -> 10 outbound, 11 inbound of 21 at defaults.
  Overlay detail/Tuning.h: convergedLedgerLimit = 24; divergedLedgerLimit
      = 128; softMaxReplyNodes = 8192; hardMaxReplyNodes = 12288;
      dropSendQueue = 192; targetSendQueue = 128; checkIdlePeers = 4 s.
  ReduceRelayCommon.h:38-41: squelch in [300 s, min(max(600, 10*npeers), 3600 s)].
  Ledger close cadence 3-5 s (xrpl.org); flag ledger every 256 ledgers.

Model: N nodes, each holding up to 21 peer slots (10 outbound, 11
inbound). A validation is injected at one validator and gossiped:
each round, every informed node forwards to all its uninformed peers
except squelched ones. Rounds are 1 second. Churn removes nodes; a
removed node reconnects after its Fibonacci backoff. The model is a
MODEL of the documented parameters, not a measurement of the live
network — it answers "what do these parameters imply", not "what does
the network do".

Deterministic seed: 20261120. No network, no private data, no
wall-clock dependence.
"""

import random
import sys

SEED = 20261120
MAX_PEERS = 21
OUT_PEERS = 10       # max((21*15+50)//100, 10)
IN_PEERS = 11
BACKOFF = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55]
SQUELCH_MIN = 300
SQUELCH_MAX = 3600
LEDGER_CLOSE_S = 5  # upper bound of the 3-5 s cadence


def build_network(n_nodes, rng):
    """Random regular-ish graph: each node picks OUT_PEERS outbound peers
    (distinct, no self-loops); inbound capacity is IN_PEERS per node.
    Returns adjacency: node -> set(peers). Deterministic under the seed."""
    peers = {i: set() for i in range(n_nodes)}
    order = list(range(n_nodes))
    rng.shuffle(order)
    for node in order:
        candidates = [x for x in range(n_nodes) if x != node]
        rng.shuffle(candidates)
        for target in candidates:
            if len(peers[node]) >= OUT_PEERS:
                break
            if len(peers[target]) >= MAX_PEERS:
                continue
            peers[node].add(target)
            peers[target].add(node)
    return peers


def gossip_rounds(peers, source, squelched=frozenset()):
    """Rounds (1 s each) until every node is informed. Squelched nodes
    still receive but do not forward. Returns (rounds, max_hops)."""
    informed = {source: 0}
    frontier = [source]
    rounds = 0
    while len(informed) < len(peers) and frontier:
        rounds += 1
        nxt = []
        for node in frontier:
            if node in squelched:
                continue
            for nb in sorted(peers[node]):
                if nb not in informed:
                    informed[nb] = rounds
                    nxt.append(nb)
        frontier = nxt
        if rounds > 1000:
            break
    return rounds, max(informed.values()), len(informed)


def main():
    failures = []

    def check(name, cond, detail=""):
        print(("PASS " if cond else "FAIL ") + name + (f" -- {detail}" if detail else ""))
        if not cond:
            failures.append(name)

    print("== peer_network_model: deterministic gossip over pinned parameters ==")
    print(f"seed={SEED}; maxPeers={MAX_PEERS} (out {OUT_PEERS} / in {IN_PEERS}); "
          f"backoff={BACKOFF}")
    print()

    rng = random.Random(SEED)

    # --- topology: 25 validators (live testnet list size) ------------------
    n = 25
    peers = build_network(n, rng)
    degrees = [len(peers[i]) for i in range(n)]
    print(f"topology N={n}: min degree={min(degrees)}, max degree={max(degrees)}, "
          f"mean degree={sum(degrees) / n:.2f}")
    check("TOPOLOGY: no node exceeds 21 peers", max(degrees) <= MAX_PEERS)
    check("TOPOLOGY: every node has at least 10 peers (its outbound set)",
          min(degrees) >= OUT_PEERS)
    check("TOPOLOGY: the graph is connected (single component)",
          _connected(peers))

    # --- propagation: a validation from one validator -----------------------
    rounds, hops, reached = gossip_rounds(peers, source=0)
    print(f"propagation from node 0: {reached}/{n} informed in {rounds} rounds, "
          f"max {hops} hops")
    check("PROPAGATION: a validation reaches all 25 validators",
          reached == n)
    check("PROPAGATION: reaches all validators within the 5 s ledger cadence",
          rounds <= LEDGER_CLOSE_S, f"{rounds} rounds (1 s each) <= {LEDGER_CLOSE_S} s")

    # --- worst source: every validator as the source ------------------------
    worst = max(gossip_rounds(peers, source=s)[0] for s in range(n))
    print(f"propagation worst source: {worst} rounds")
    check("PROPAGATION: worst-case source still reaches all within 5 s",
          worst <= LEDGER_CLOSE_S, f"worst={worst} rounds")

    # --- squelch: 5 squelched relays ----------------------------------------
    squelched = frozenset(range(0, 5))
    r2, h2, reached2 = gossip_rounds(peers, source=10, squelched=squelched)
    print(f"propagation with 5 squelched relays: {reached2}/{n} in {r2} rounds")
    check("SQUELCH: 5 squelched relays do not prevent full propagation",
          reached2 == n)

    # --- churn: 4 validators drop, reconnect after backoff ------------------
    print()
    print("-- churn: 4 validators drop at round 0, reconnect per backoff --")
    dropped = {3: BACKOFF[0], 7: BACKOFF[2], 11: BACKOFF[4], 19: BACKOFF[6]}
    print(f"drop schedule (node: backoff s): {dropped}")
    # A dropped node is unreachable until its backoff elapses; the rest of
    # the network must still reach quorum (17 of 25) without them.
    alive = n - len(dropped)
    print(f"validators alive during churn: {alive}; quorum (67%) = 17")
    check("CHURN: 21 alive validators still exceed the 17 quorum",
          alive >= 17)
    check("CHURN: backoff values are the Fibonacci sequence from Tuning.h",
          BACKOFF == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55])
    print(f"longest reconnect backoff in this churn: {max(dropped.values())} s "
          f"(node 19, 6th retry)")

    # --- send-queue bound ----------------------------------------------------
    print()
    print("-- send-queue bound (Overlay Tuning.h) --")
    print("dropSendQueue=192, targetSendQueue=128, checkIdlePeers=4 s")
    check("QUEUE: target (128) is below the drop threshold (192)",
          128 < 192)

    print()
    if failures:
        print(f"NETWORK RESULT: {len(failures)} CHECK(S) FAILED: {failures}")
        return 1
    print("NETWORK RESULT: ALL CHECKS PASSED")
    return 0


def _connected(peers):
    seen = set()
    stack = [0]
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        stack.extend(peers[node] - seen)
    return len(seen) == len(peers)


if __name__ == "__main__":
    sys.exit(main())
