# Agent-Integration Contract — PROPOSAL

**Status: PROPOSAL, version `pf.contract.v1-proposal` (2026-11-21).**
This is not a specification of the platform. No public specification
exists: the public page at https://tasknode.postfiat.org/ (fetched
2026-11-20) renders only the text "What are you working on?" — no
documentation, no API reference, and no public repository for the
platform was found. No login was attempted and no authenticated
endpoint was probed.

What follows is derived from the **observable flow** — the sequence of
events a participant can see when a task is offered, accepted, worked,
checked, and settled — and it is labelled as a proposal throughout.
The conformance harness `scripts/contract_conformance.py` (N-07)
checks that this proposal is internally consistent and that its rules
reject malformed sequences. It does not test the live platform.

## 1. The observed flow

[FAKTA] The observable event sequence, as recorded 2026-11-20:

```
Offered -> Accepted -> Submitted -> verification requested ->
verification response -> settlement outcome
```

[FAKTA] Evidence types observed in the submitted step: **URL** (a
link to a public reference), **commit** (a commit or pull-request
URL), and **text** (a written summary). No other evidence type was
observed.

[FAKTA] Settlement outcomes carry five fields: a numeric value, a
completion score, an evidence-quality score, a transaction hash, and a
content identifier (CID).

[ANALISIS] Two properties of the flow are worth naming because the
contract is built around them. First, verification is a round-trip:
a question is asked, exactly one response follows, and only then does
a settlement outcome appear. Second, a task that has been submitted
but received no platform message is in an indeterminate state — it is
flagged as awaiting a response, never assumed settled. The harness
encodes both properties (rules R3/R5 and the liveness check).

## 2. Proposed event schemas

All events carry `task_id` (string) and `type` (string). Field types
below are the proposal; the platform publishes none of this.

### 2.1 `pf.task.offered.v1`

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | platform-assigned identifier |
| `title` | string | human-readable task title |
| `value` | number | offered value, in the platform's native unit |
| `scale` | string | `personal` \| `network` — the two scales observed |

### 2.2 `pf.task.accepted.v1`

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | must match a preceding `offered` event for the same task |

### 2.3 `pf.task.submitted.v1`

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | must match a preceding `accepted` event |
| `evidence` | array, non-empty | one or more evidence items (see §2.4) |

### 2.4 Evidence items

| Field | Type | Notes |
|---|---|---|
| `kind` | string | exactly one of `url`, `commit`, `text` |
| `ref` | string, non-empty | URL for `url`/`commit`; the text itself for `text` |
| `note` | string, optional | what the item shows |

[ANALISIS] Three kinds are enough to cover everything observed, and
the closed set is deliberate: an open-ended kind field would let a
screenshot, a binary blob, or a private link pass as evidence without
any checkable content. A future revision that needs a fourth kind
should add it to the set explicitly, with a rule for what a reviewer
checks in it — not by widening the field.

### 2.5 `pf.task.verification_request.v1`

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | |
| `question` | string, non-empty | the question asked about the delivered work |

### 2.6 `pf.task.verification_response.v1`

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | |
| `answer` | string, non-empty | the answer |
| `cites` | array of strings, optional | pinned sources the answer rests on (file:line or URL) |

### 2.7 `pf.task.settlement.v1`

| Field | Type | Notes |
|---|---|---|
| `value` | number | settled value |
| `completion_score` | number, 0–100 | |
| `evidence_score` | number, 0–100 | |
| `tx_hash` | string, 64 hex chars | on-chain transaction hash of the settlement |
| `cid` | string, non-empty | content identifier of the settled work |

## 3. Rules the harness enforces

| Rule | Statement | Harness check |
|---|---|---|
| R1 | Event order is Offered, Accepted, Submitted, then any number of (verification request, verification response) pairs, then at most one settlement event. | `check_sequence`, order + duplicate checks |
| R2 | Every evidence item has kind `url` \| `commit` \| `text` and a non-empty `ref`. | evidence loop in `check_sequence` |
| R3 | Every verification request is answered by exactly one verification response before any settlement event. | open-request counting |
| R4 | A settlement event carries all five fields with the right shapes (scores in 0–100, `tx_hash` 64 hex chars, `cid` non-empty). | field-shape checks |
| R5 | No settlement event may appear while a verification request is unanswered. | open-request check at settlement |

[FAKTA] The harness also runs six negative cases, each of which must
be rejected: settlement without `tx_hash`; evidence kind
`screenshot`; settlement before the verification response; two
responses to one request; `completion_score` 101; a delivery with no
evidence items (`outputs/contract_conformance.log`).

[FAKTA] Liveness: a sequence that ends at the submitted step is
shape-conformant but incomplete — the harness reports "no settlement
event" rather than inferring one. A participant watching such a task
should treat it as awaiting a platform response, not as settled.

## 4. Explicit gaps — what would make this verifiable

[ANALISIS] The proposal is checkable as a document, but it cannot be
verified against the platform until the platform publishes the
following. Each gap is stated plainly so a reader can see exactly
what is assumed.

1. **No published event schema.** The field names, types, and the
   `pf.*` namespace above are the proposal's invention. The platform
   could use different names, nest fields differently, or carry the
   same information in a form this contract does not model. Until a
   schema is published, conformance can only be checked against the
   proposal, not against the platform.
2. **No public endpoint or authentication model.** There is no
   documented way for an agent to list offered tasks, accept one,
   deliver work, or poll for verification requests without using the
   web session. The contract describes events, not transport.
   [ANALISIS] A minimal verifiable addition would be a read-only
   public endpoint for task status plus a documented delivery
   endpoint — without either, every integration is screen-scraping
   by another name.
3. **No published settlement semantics.** The five settlement fields
   are observed, but how `completion_score` and `evidence_score` are
   computed, what partial settlement means, and how disputes are
   handled are not documented. The proposal records the fields; it
   does not invent the scoring rule.
4. **No versioning or change notice.** The proposal is versioned
   (`pf.contract.v1-proposal`) precisely because the platform's
   behaviour can change without notice. A published contract would
   need a version field on every event and a changelog.
5. **No liveness guarantee.** Nothing in the observed flow bounds how
   long a submitted task may wait for a verification request or a
   settlement. The harness flags the wait; it cannot bound it.

[ANALISIS] The honest summary: this contract is a testable statement
of what the observable flow appears to be, built so that the moment
the platform publishes a real specification, the same harness can be
pointed at real event data and the differences measured — instead of
arguing from memory about what the flow was.
